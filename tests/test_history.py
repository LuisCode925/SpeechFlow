"""Tests de speechflow.history."""
import json
import stat
import threading

import pytest

from speechflow.history import HISTORY_BACKUP_COUNT, History


def entrada(texto="Hola, mundo.", **extra):
    return {"ts": "2026-10-13T10:42:07.318-05:00", "text": texto, "original": texto, "language": "es",
            "model": "small", "audio_seconds": 2.4, "seconds": 0.61, **extra}


def lineas(ruta):
    return ruta.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def ruta(tmp_path):
    return tmp_path / "state" / "history.jsonl"


class TestAdd:
    def test_una_linea_json_por_add(self, ruta):
        h = History(ruta, 1_000_000)
        h.add(entrada("uno"))
        h.add(entrada("dos"))
        h.close()
        filas = [json.loads(linea) for linea in lineas(ruta)]
        assert [f["text"] for f in filas] == ["uno", "dos"]
        assert set(filas[0]) == {"ts", "text", "original", "language", "model", "audio_seconds", "seconds"}

    def test_acentos_sin_escapar(self, ruta):
        h = History(ruta, 1_000_000)
        h.add(entrada("¿Qué hará el niño? Sí, él está allá."))
        h.close()
        contenido = ruta.read_text(encoding="utf-8")
        assert "¿Qué hará el niño?" in contenido
        assert "\\u" not in contenido

    def test_salto_de_linea_ocupa_una_linea(self, ruta):
        h = History(ruta, 1_000_000)
        h.add(entrada("a\nb"))
        h.close()
        assert len(lineas(ruta)) == 1
        assert json.loads(lineas(ruta)[0])["text"] == "a\nb"

    def test_crea_la_carpeta(self, ruta):
        History(ruta, 1_000_000).close()
        assert ruta.parent.is_dir()

    def test_add_tras_close_no_escribe(self, ruta):
        h = History(ruta, 1_000_000)
        h.close()
        h.add(entrada())
        assert lineas(ruta) == []

    def test_close_dos_veces(self, ruta):
        h = History(ruta, 1_000_000)
        h.close()
        h.close()

    def test_carpeta_no_escribible_lanza_oserror(self, tmp_path):
        bloqueo = tmp_path / "archivo"
        bloqueo.write_text("x")
        with pytest.raises(OSError):
            History(bloqueo / "history.jsonl", 1_000_000)


class TestRotacion:
    def test_rota_al_superar_max_bytes(self, ruta):
        h = History(ruta, 300)
        for i in range(4):
            h.add(entrada(f"dictado {i}"))
        h.close()
        rotado = ruta.with_name("history.jsonl.1")
        assert rotado.is_file()
        assert json.loads(lineas(rotado)[-1])["text"] != "dictado 3"
        assert json.loads(lineas(ruta)[-1])["text"] == "dictado 3"

    def test_nunca_mas_de_dos_copias(self, ruta):
        h = History(ruta, 200)
        for i in range(30):
            h.add(entrada(f"dictado {i}"))
        h.close()
        nombres = sorted(p.name for p in ruta.parent.iterdir())
        assert nombres == ["history.jsonl", "history.jsonl.1", "history.jsonl.2"]
        assert HISTORY_BACKUP_COUNT == 2

    def test_ninguna_linea_partida(self, ruta):
        h = History(ruta, 250)
        for i in range(20):
            h.add(entrada(f"dictado {i}"))
        h.close()
        for archivo in ruta.parent.iterdir():
            for linea in lineas(archivo):
                json.loads(linea)

    def test_orden_de_rotados(self, ruta):
        h = History(ruta, 200)
        for i in range(30):
            h.add(entrada(f"d{i:02d}"))
        h.close()
        def textos(nombre):
            return [json.loads(linea)["text"] for linea in lineas(ruta.with_name(nombre))]
        assert textos("history.jsonl.2")[-1] < textos("history.jsonl.1")[0]
        assert textos("history.jsonl.1")[-1] < textos("history.jsonl")[0]


class TestPermisos:
    def test_activo_y_rotados_0600(self, ruta):
        h = History(ruta, 200)
        for i in range(30):
            h.add(entrada(f"dictado {i}"))
        h.close()
        archivos = list(ruta.parent.iterdir())
        assert len(archivos) == 3
        for archivo in archivos:
            assert stat.S_IMODE(archivo.stat().st_mode) == 0o600


class TestHilos:
    def test_dos_hilos_no_mezclan_lineas(self, ruta):
        h = History(ruta, 10_000_000)
        n = 200

        def escribir(prefijo):
            for i in range(n):
                h.add(entrada(f"{prefijo} {i} " + "x" * 200))

        hilos = [threading.Thread(target=escribir, args=(p,)) for p in ("A", "B")]
        for t in hilos:
            t.start()
        for t in hilos:
            t.join()
        h.close()
        filas = [json.loads(linea) for linea in lineas(ruta)]
        assert len(filas) == 2 * n
