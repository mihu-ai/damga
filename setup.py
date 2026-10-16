import glob
import os
import sys

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

HERE = os.path.dirname(os.path.abspath(__file__))
OPENFST = os.path.join(HERE, "third_party", "openfst", "src")

sources = ["src/damga_fstrt.cc"] + sorted(glob.glob(os.path.join(OPENFST, "lib", "*.cc")))
defines = [("FST_NO_DYNAMIC_LINKING", "1")]
if sys.platform == "win32":
    cflags = ["/O2", "/EHsc", "/bigobj", "/utf-8", "/wd4244", "/wd4267", "/wd4996"]
    defines += [("NOMINMAX", "1"), ("_USE_MATH_DEFINES", "1")]
else:
    cflags = ["-O2", "-fvisibility=hidden", "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-deprecated-declarations"]

ext = Pybind11Extension(
    "damga._fstrt",
    sources=[os.path.relpath(s, HERE) for s in sources],
    include_dirs=[os.path.join(OPENFST, "include")],
    define_macros=defines,
    extra_compile_args=cflags,
    cxx_std=17,
)

setup(ext_modules=[ext], cmdclass={"build_ext": build_ext})
