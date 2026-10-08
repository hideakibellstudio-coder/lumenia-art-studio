"""The engine judges licenses, marks unlicensed exports and writes crash dumps (white box of bind_runtime.cpp).

The tokens below were signed by the generator's `test` key (lumenia-license-generator,
2026-10-08), which no build trusts: `license_evaluate` checks them against that key
without touching the license of the process. The signature is checked by Windows
CNG, so elsewhere every license is "unsupported" and those cases are skipped.
"""
from __future__ import annotations

import sys

import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")

TEST_PUBLIC_KEY = bytes.fromhex(
    "68effa7fac856c5204eb2c85afb30f78a65deef2965fdb32512a84fb07727f89"
    "64ec0c7df6bf7c6ae288beafc655ea54e9db5888d16f4260a7ae9d3ec4fc30e5")
VALID = (
    "LUMENIA1-OY6TCCTJMQ6UYLKUGAYDAMBRBJZWW5J5OBZG6CTOMFWWKPKUMVZXIZJAMRQSAU3JNR3GCCTNMFUWYPLBMY2GEMRUMNSDEYRQ"
    "MQZGEZDBHFTDGOLEGFSGMZLFGA2TSNTFGUZTMMLBGYZDMZRZMVTDQY3GGEZWEMZZG5QTCNZWMQYDGZRTGJTGECTJMF2D2MRQGI3C2MJQ"
    "FUYDQCTVOBSD2MRQGI3S2MJQFUYDQCQ.N33O2WI2D6CZSJQZVPDEBH2ERZRDJERAM4A4XLYG644LJCQRCRVF7KXBDFM32NPS6EUAJZJS"
    "NNOEKLA743ZT4MMSXAJLVX4G2JYAB3I")
EXPIRED = (
    "LUMENIA1-OY6TCCTJMQ6UYLKUGAYDAMBSBJZWW5J5OBZG6CTOMFWWKPKUMVZXIZJAMRQSAU3JNR3GCCTNMFUWYPLBMY2GEMRUMNSDEYRQ"
    "MQZGEZDBHFTDGOLEGFSGMZLFGA2TSNTFGUZTMMLBGYZDMZRZMVTDQY3GGEZWEMZZG5QTCNZWMQYDGZRTGJTGECTJMF2D2MRQGI3C2MJQ"
    "FUYDQCTVOBSD2MRQGI3S2MJQFUYDQCTFPBYD2MRQGI3C2MBRFUYDCCQ.MQ5IEFO5JZJHKZWKSPGLF66Z375HFNASU2E7D6VWYEVNJE7G"
    "KK3KBBWLVDF5OI43ZPT47BYELUI6N3N2EXA7SMTADWYAWUZFQCFHG2I")
UPDATES_EXPIRED = (
    "LUMENIA1-OY6TCCTJMQ6UYLKUGAYDAMBTBJZWW5J5OBZG6CTOMFWWKPKUMVZXIZJAMRQSAU3JNR3GCCTNMFUWYPLBMY2GEMRUMNSDEYRQ"
    "MQZGEZDBHFTDGOLEGFSGMZLFGA2TSNTFGUZTMMLBGYZDMZRZMVTDQY3GGEZWEMZZG5QTCNZWMQYDGZRTGJTGECTJMF2D2MRQGI3C2MJQ"
    "FUYDQCTVOBSD2MRQGI3C2MBRFUYDCCQ.CIPRD2Q62P3OFMXLQ46RWXOPOQ3KOTSDG3UKLR2OUA5BO7OGTG3DWBTGJWA7BZRWLUDHVI6K"
    "BZOSYWCQYIO5MAV7XYJNRJ6FYAYM34A")
MACHINE_BOUND = (
    "LUMENIA1-OY6TCCTJMQ6UYLKUGAYDAMBUBJZWW5J5OBZG6CTOMFWWKPKUMVZXIZJAMRQSAU3JNR3GCCTNMFUWYPLBMY2GEMRUMNSDEYRQ"
    "MQZGEZDBHFTDGOLEGFSGMZLFGA2TSNTFGUZTMMLBGYZDMZRZMVTDQY3GGEZWEMZZG5QTCNZWMQYDGZRTGJTGECTJMF2D2MRQGI3C2MJQ"
    "FUYDQCTVOBSD2MRQGI3S2MJQFUYDQCTNNFSD2YLCMMFA.KRPRFBHPILFXGHH7CLXUGWGCQSHKHKKV3RHL4SHK5RJFYXBEYNABJHMNR6T7"
    "DXTHBXBS67UGN3Z4BBT7KTJ7RT4BF6SIXPJ5BP4LR3Q")
# The generator's `dev` key: compiled into development builds until `export --key prod`.
DEV_KEY_ID = "488521e11bcd7b57"
DEV_VALID = (
    "LUMENIA1-OY6TCCTJMQ6UYLKEGAYDAMBRBJZWW5J5OBZG6CTOMFWWKPKUMVZXIZJAMRQSAU3JNR3GCCTNMFUWYPLBMY2GEMRUMNSDEYRQ"
    "MQZGEZDBHFTDGOLEGFSGMZLFGA2TSNTFGUZTMMLBGYZDMZRZMVTDQY3GGEZWEMZZG5QTCNZWMQYDGZRTGJTGECTJMF2D2MRQGI3C2MJQ"
    "FUYDQCQ.FVRLKMELSGJMMTONSF2YFHSY7SRFWXQ4YINUYVZ6DRMN7K3IABBXNPGE7QBZMXADCBSJGHEUJ7J4E7N54HZ4W73UQPSFWT6NJFA2WOY")

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="signatures are checked by Windows CNG")


def _evaluate(token: str, today: str = "2026-10-08", build: str = "2026-10-08", key: bytes = TEST_PUBLIC_KEY) -> dict:
    return native.license_evaluate(token, today, build, key)


@windows_only
def test_a_signed_license_is_licensed_and_names_its_holder():
    status = _evaluate(VALID)
    assert status["state"] == "licensed"
    assert (status["license_id"], status["sku"], status["holder_name"]) == ("L-T00001", "pro", "Teste da Silva")
    assert (status["issued_on"], status["updates_until"], status["expires_on"]) == ("2026-10-08", "2027-10-08", "")


@windows_only
def test_a_license_wrapped_by_an_email_client_still_reads():
    wrapped = "\n".join(VALID[i:i + 64] for i in range(0, len(VALID), 64))
    assert _evaluate("  " + wrapped + "\n")["state"] == "licensed"


@windows_only
@pytest.mark.parametrize("token,today,build,state", [
    (EXPIRED, "2026-10-08", "2026-10-08", "expired"),
    (EXPIRED, "2025-12-31", "2025-12-31", "licensed"),
    (UPDATES_EXPIRED, "2026-10-08", "2026-10-08", "updates_expired"),
    (UPDATES_EXPIRED, "2026-10-08", "2025-12-01", "licensed"),
    (MACHINE_BOUND, "2026-10-08", "2026-10-08", "unsupported"),
])
def test_dates_and_machine_binding_decide_the_state(token, today, build, state):
    assert _evaluate(token, today, build)["state"] == state


@windows_only
def test_another_key_or_a_changed_byte_is_a_bad_signature():
    assert _evaluate(VALID, key=bytes(64))["state"] in ("bad_signature",)
    payload, signature = VALID.split(".")
    flipped = payload[:-12] + ("A" if payload[-12] != "A" else "B") + payload[-11:] + "." + signature
    assert _evaluate(flipped)["state"] in ("bad_signature", "malformed")


@pytest.mark.parametrize("garbage", ["", "LUMENIA1-", "LUMENIA2-AAAA.BBBB", "LUMENIA1-AA!A.BBBB", VALID.replace(".", "")])
def test_what_is_not_a_token_is_malformed(garbage):
    assert _evaluate(garbage)["state"] == "malformed"


def test_a_public_key_of_the_wrong_size_is_a_value_error():
    with pytest.raises(ValueError):
        native.license_evaluate(VALID, "2026-10-08", "2026-10-08", b"short")


def test_a_bad_key_never_replaces_the_active_license():
    native.license_clear()
    assert native.license_apply("LUMENIA1-AAAA.BBBB")["state"] == "malformed"
    assert native.license_status()["state"] == "unlicensed"


def test_build_date_and_key_id_are_exposed():
    import re

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", native.license_build_date())
    assert re.fullmatch(r"[0-9a-f]{16}", native.license_key_id())


def test_an_unlicensed_export_is_watermarked_and_the_buffer_is_checked():
    native.license_clear()
    blank = bytes(320 * 240 * 4)
    stamped = native.apply_export_policy(blank, 320, 240)
    assert len(stamped) == len(blank) and stamped != blank
    alpha_touched = sum(1 for i in range(3, len(stamped), 4) if stamped[i])
    assert 0.01 < alpha_touched / (320 * 240) < 0.4, "the mark must show without covering the picture"
    with pytest.raises(ValueError):
        native.apply_export_policy(blank[:-1], 320, 240)


@windows_only
def test_a_licensed_export_leaves_the_pixels_alone():
    if native.license_key_id() != DEV_KEY_ID:
        pytest.skip("this build trusts the production key (export --key prod)")
    try:
        assert native.license_apply(DEV_VALID)["state"] == "licensed"
        pixels = bytes(range(256)) * (64 * 64 * 4 // 256)
        assert native.apply_export_policy(pixels, 64, 64) is pixels
    finally:
        native.license_clear()


@windows_only
def test_the_crash_handler_takes_a_folder_and_a_manual_dump_is_written(tmp_path):
    assert native.install_crash_handler(str(tmp_path))
    assert not native.install_crash_handler(str(tmp_path / "missing"))
    dump = tmp_path / "manual.dmp"
    assert native.write_diagnostic_dump(str(dump))
    assert dump.read_bytes()[:4] == b"MDMP"
