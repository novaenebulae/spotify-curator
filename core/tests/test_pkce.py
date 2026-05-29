from app.spotify.pkce import code_challenge_s256


def test_code_challenge_s256_known_vector() -> None:
    # RFC 7636 Appendix B
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert code_challenge_s256(verifier) == expected

