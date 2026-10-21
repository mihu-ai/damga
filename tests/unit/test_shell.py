import pytest

from damga import shell_form
from damga.tr.shell import SHELL_SYMBOLS, spell_letters


@pytest.mark.parametrize("src,expected", [
    ("LS tire lah.", "ls -lah"),
    ("ls boşluk tire lah", "ls -lah"),
    ("el es tire lah", "ls -lah"),
    ("el estireler", "ls -ler"),
    ("ls eksi lah", "ls -lah"),
    ("ls minus lah", "ls -lah"),
    ("ls maynus lah", "ls -lah"),
    ("ls tire l tire a", "ls -l -a"),
    ("git çift tire version", "git --version"),
    ("git eksi eksi version", "git --version"),
    ("git push tire tire force", "git push --force"),
    ("git double dash help", "git --help"),
    ("git add nokta", "git add ."),
    ("git commit tire m çift tırnak düzeltme yapıldı çift tırnak", 'git commit -m "düzeltme yapıldı"'),
    ("Cd slash tmp.", "cd /tmp"),
    ("sidislaş tmp", "cd /tmp"),
    ("cd nokta nokta", "cd .."),
    ("cd bölü tmp", "cd /tmp"),
    ("cd tilde slash projeler", "cd ~/projeler"),
    ("cat slash etc slash hosts", "cat /etc/hosts"),
    ("ls src slash main", "ls src/main"),
    ("ls tire la slash tmp", "ls -la /tmp"),
    ("cat dosya nokta txt", "cat dosya.txt"),
    ("kat dosya dot txt", "cat dosya.txt"),
    ("nokta slash run nokta sh", "./run.sh"),
    ("rm yıldız nokta pyc", "rm *.pyc"),
    ("chmod artı x run nokta sh", "chmod +x run.sh"),
    ("Ps aux boru grep Python.", "ps aux | grep python"),
    ("ps aux pipe grep node", "ps aux | grep node"),
    ("npm install ve ve npm test", "npm install && npm test"),
    ("sleep 10 ampersand", "sleep 10 &"),
    ("ls büyüktür liste nokta txt", "ls > liste.txt"),
    ("echo merhaba çift büyüktür log nokta txt", "echo merhaba >> log.txt"),
    ("sort küçüktür liste", "sort < liste"),
    ("curl localhost iki nokta üst üste 8.000", "curl localhost:8000"),
    ("export a eşittir b", "export a=b"),
    ("echo dolar home", "echo $home"),
    ("ssh deniz et işareti sunucu", "ssh deniz@sunucu"),
    ("cat my underscore file nokta py", "cat my_file.py"),
    ("echo parantez aç a b parantez kapat", "echo (a b)"),
    ("python3 tire c print parantez aç 1 parantez kapat", "python3 -c print(1)"),
    ("echo tek tırnak a tek tırnak", "echo 'a'"),
    ("echo a virgül b", "echo a,b"),
    ("head tire n 10 dosya nokta txt", "head -n 10 dosya.txt"),
    ("ls backslash", "ls \\"),
    ("if a büyük eşit b", "if a >= b"),
    ("if a küçük eşittir b", "if a <= b"),
    ("test a eşit eşit b", "test a == b"),
    ("test a eşit değil b", "test a != b"),
    ("x artı eşittir 1", "x += 1"),
    ("x eksi eşittir 1", "x -= 1"),
    ("a çift boru b", "a || b"),
    ("cat çift küçüktür eof", "cat << eof"),
    ("echo 2 artı 3", "echo 2 + 3"),
    ("echo 10 bölü 2", "echo 10 / 2"),
    ("echo 4 çarpı 5", "echo 4 * 5"),
    ("echo 2 üzeri 10", "echo 2 ^ 10"),
    ("echo 10 mod 3", "echo 10 % 3"),
    ("echo 2 çift yıldız 8", "echo 2 ** 8"),
    ("echo 7 eksi 2", "echo 7 - 2"),
    ("echo x artı y", "echo x + y"),
    ("i artı artı", "i++"),
    ("chmod artı x run nokta sh", "chmod +x run.sh"),
    ("head tire n 10", "head -n 10"),
    ("ls tire el a haş", "ls -lah"),
    ("ls tire l a h", "ls -lah"),
    ("el a haş", "lah"),
    ("ls tire eyç", "ls -h"),
    ("tar tire iks ve ef", "tar -xvf"),
    ("grep tire ar ay", "grep -ri"),
    ("ps tire e ef", "ps -ef"),
    ("git commit tire em çift tırnak test çift tırnak", 'git commit -m "test"'),
    ("cp a b", "cp a b"),
    ("echo a", "echo a"),
    ("sudo p a s s W d", "sudo passwd"),
    ("ls tire l a h", "ls -lah"),
])
def test_shell_form(src, expected):
    assert shell_form(src) == expected


@pytest.mark.parametrize("text", ["ls", "git status", "npm test", "make", ""])
def test_shell_form_leaves_plain_commands_alone(text):
    assert shell_form(text) == text


def test_every_symbol_is_read():
    for symbol, forms in SHELL_SYMBOLS:
        for spoken in forms:
            got = shell_form(f"echo {spoken} x")
            assert symbol in got if symbol else got == "echo x", (spoken, got)


def test_shell_form_is_turkish_only():
    with pytest.raises(ValueError):
        shell_form("ls dash la", lang="en")


@pytest.mark.parametrize("src,expected", [
    ("pi ey es es dabılyu di", "passwd"),
    ("pe a se se çift ve de", "passwd"),
    ("sudo pi ey es es dabılyu di", "sudo passwd"),
    ("ls tire el a haş", "ls tire lah"),
    ("ce ha em o de artı iks", "chmod artı x"),
    ("curl localhost iki nokta üst üste sekiz bin", "curl localhost iki nokta üst üste sekiz bin"),
    ("cd nokta nokta", "cd nokta nokta"),
])
def test_spell_letters_joins_only_letters(src, expected):
    """Run before ITN: letters are joined, symbols and number words stay as said for ITN."""
    assert spell_letters(src) == expected
