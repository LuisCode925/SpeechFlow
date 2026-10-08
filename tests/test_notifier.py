"""Tests de speechflow.notifier contra el doble de subprocess.run."""
from speechflow import notifier


def test_notify_llama_a_notify_send(subprocess_falso):
    notifier.notify("Título", "cuerpo")
    assert subprocess_falso == [((["notify-send", "Título", "cuerpo"],), {"check": False})]


def test_notify_cuerpo_vacio_por_defecto(subprocess_falso):
    notifier.notify("Título")
    assert subprocess_falso[0][0][0] == ["notify-send", "Título", ""]


def test_set_enabled_false_silencia(subprocess_falso):
    notifier.set_enabled(False)
    notifier.notify("Título")
    assert subprocess_falso == []


def test_set_enabled_true_reactiva(subprocess_falso):
    notifier.set_enabled(False)
    notifier.set_enabled(True)
    notifier.notify("Título")
    assert len(subprocess_falso) == 1


def test_notify_sin_notify_send_no_falla(monkeypatch):
    def run(*args, **kwargs):
        raise FileNotFoundError("notify-send")

    monkeypatch.setattr(notifier.subprocess, "run", run)
    notifier.notify("Título")  # no debe lanzar
