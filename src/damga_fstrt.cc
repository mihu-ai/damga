#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <fst/arcsort.h>
#include <fst/compose.h>
#include <fst/project.h>
#include <fst/rmepsilon.h>
#include <fst/fst.h>
#include <fst/shortest-path.h>
#include <fst/vector-fst.h>

#include <algorithm>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace {

using fst::StdArc;
using fst::StdFst;
using fst::StdVectorFst;
using Weight = StdArc::Weight;

class Grammar {
 public:
  explicit Grammar(const std::string &path) {
    std::unique_ptr<StdFst> raw(StdFst::Read(path));
    if (!raw) throw std::runtime_error("damga: cannot read FST: " + path);
    fst_ = std::make_unique<StdVectorFst>(*raw);
    fst::ArcSort(fst_.get(), fst::ILabelCompare<StdArc>());
    path_ = path;
  }

  explicit Grammar(const py::bytes &blob) {
    std::string data = blob;
    std::istringstream strm(data, std::ios::in | std::ios::binary);
    std::unique_ptr<StdFst> raw(StdFst::Read(strm, fst::FstReadOptions("<bytes>")));
    if (!raw) throw std::runtime_error("damga: cannot read FST from bytes");
    fst_ = std::make_unique<StdVectorFst>(*raw);
    fst::ArcSort(fst_.get(), fst::ILabelCompare<StdArc>());
    path_ = "<bytes>";
  }

  // Python objects are only touched with the GIL held: the argument arrives as a std::string (converted by pybind11
  // before the call) and the result becomes bytes after the GIL is taken back.  Only the OpenFst work runs without
  // it, so threads normalize in parallel.  Creating py::bytes without the GIL corrupted the interpreter's heap.
  py::object rewrite(const std::string &input) const {
    std::optional<std::string> out;
    {
      py::gil_scoped_release release;
      out = run(input);
    }
    if (!out) return py::none();
    return py::bytes(*out);
  }

  // The n best distinct outputs with their costs, best first (variants: every reading of a sentence).
  py::list rewrite_nbest(const std::string &input, int n) const {
    std::vector<std::pair<float, std::string>> outs;
    {
      py::gil_scoped_release release;
      outs = run_nbest(input, n);
    }
    py::list result;
    for (const auto &o : outs) result.append(py::make_tuple(py::bytes(o.second), o.first));
    return result;
  }

  int64_t num_states() const { return fst_->NumStates(); }
  const std::string &path() const { return path_; }

 private:
  StdVectorFst compose(const std::string &in) const {
    StdVectorFst chain;
    auto s = chain.AddState();
    chain.SetStart(s);
    for (unsigned char c : in) {
      auto n = chain.AddState();
      chain.AddArc(s, StdArc(c, c, Weight::One(), n));
      s = n;
    }
    chain.SetFinal(s, Weight::One());
    StdVectorFst lattice;
    fst::Compose(chain, *fst_, &lattice);
    return lattice;
  }

  std::vector<std::pair<float, std::string>> run_nbest(const std::string &in, int n) const {
    std::vector<std::pair<float, std::string>> outs;
    StdVectorFst lattice = compose(in);
    if (lattice.Start() == fst::kNoStateId || n < 1) return outs;
    // Distinct outputs: keep the output side only, so paths that write the same text count once.
    fst::Project(&lattice, fst::ProjectType::OUTPUT);
    fst::RmEpsilon(&lattice);
    StdVectorFst best;
    fst::ShortestPath(lattice, &best, n, /*unique=*/true);
    if (best.Start() == fst::kNoStateId) return outs;
    // Each path leaves the start state by its own arc; collect them with their weights, best first.
    std::vector<std::pair<float, std::string>> scored;
    for (fst::ArcIterator<StdVectorFst> first(best, best.Start()); !first.Done(); first.Next()) {
      std::string out;
      float cost = first.Value().weight.Value();
      const auto &a0 = first.Value();
      if (a0.olabel != 0) out.push_back(static_cast<char>(a0.olabel));
      auto state = a0.nextstate;
      bool ok = true;
      while (best.Final(state) == Weight::Zero()) {
        fst::ArcIterator<StdVectorFst> ai(best, state);
        if (ai.Done()) { ok = false; break; }
        const auto &arc = ai.Value();
        cost += arc.weight.Value();
        if (arc.olabel != 0) out.push_back(static_cast<char>(arc.olabel));
        state = arc.nextstate;
      }
      if (ok) scored.emplace_back(cost + best.Final(state).Value(), out);
    }
    if (best.Final(best.Start()) != Weight::Zero()) scored.emplace_back(best.Final(best.Start()).Value(), "");
    std::stable_sort(scored.begin(), scored.end(),
                     [](const auto &a, const auto &b) { return a.first < b.first; });
    return scored;
  }

  std::optional<std::string> run(const std::string &in) const {
    StdVectorFst lattice = compose(in);
    if (lattice.Start() == fst::kNoStateId) return std::nullopt;
    StdVectorFst best;
    fst::ShortestPath(lattice, &best, 1);
    if (best.Start() == fst::kNoStateId) return std::nullopt;
    std::string out;
    auto state = best.Start();
    while (best.Final(state) == Weight::Zero()) {
      fst::ArcIterator<StdVectorFst> ai(best, state);
      if (ai.Done()) return std::nullopt;
      const auto &arc = ai.Value();
      if (arc.olabel != 0) out.push_back(static_cast<char>(arc.olabel));
      state = arc.nextstate;
    }
    return out;
  }

  std::unique_ptr<StdVectorFst> fst_;
  std::string path_;
};

}  // namespace

PYBIND11_MODULE(_fstrt, m) {
  m.doc() = "damga native runtime: compose + shortest path over precompiled OpenFst grammars";
  m.attr("OPENFST_VERSION") = "1.8.4";
  py::class_<Grammar>(m, "Grammar")
      .def(py::init<const std::string &>(), py::arg("path"))
      .def_static("from_bytes", [](const py::bytes &b) { return std::make_unique<Grammar>(b); }, py::arg("data"))
      .def("rewrite", &Grammar::rewrite, py::arg("input"))
      .def("rewrite_nbest", &Grammar::rewrite_nbest, py::arg("input"), py::arg("n"))
      .def_property_readonly("num_states", &Grammar::num_states)
      .def_property_readonly("path", &Grammar::path);
}
