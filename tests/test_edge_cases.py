import pytest

from ismypwdsafe import analyze_password


@pytest.mark.parametrize("pwd", [
    "",
    " ",
    "a",
    "\x00",
    "a\nb",
    "\x1b[31mred\x1b[0m",
    "a" * 10000,
    "🔒🔑",
    "P@ssw0rd\x00",
])
def test_edge_cases_do_not_crash(pwd):
    # Usa check_breach=False per evitare chiamate di rete nei test
    result = analyze_password(pwd, check_breach=False)
    
    # L'engine non deve mai lanciare eccezioni
    assert result is not None
    
    # Se la stringa è vuota o contiene solo emoji (charset 0), ci aspettiamo un errore
    if not pwd or pwd == "🔒🔑":  # noqa: S105
        assert result.error is not None
        assert result.exit_code != 0
    else:
        # Per tutti gli altri input, l'analisi deve andare a buon fine
        assert result.error is None
        assert 0 <= result.score.value <= 100