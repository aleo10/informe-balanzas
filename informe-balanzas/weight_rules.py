"""
Reglas para determinar pesas y carga máxima según CAPACIDAD de la balanza.
El tipo de balanza no influye en la elección de pesas.
"""
import math


def get_excentricidad_camiones(cap_max_kg: float, apoyos: int) -> dict:
    """
    Para balanzas de camiones:
    - n_posiciones = apoyos (de la base de datos)
    - pesa_exc = cap_max / apoyos, redondeado hacia arriba a la unidad de mil
    """
    pesa_raw = cap_max_kg / apoyos
    pesa_exc = math.ceil(pesa_raw / 1000) * 1000
    return {
        "n_posiciones": apoyos,
        "pesa_exc_kg": pesa_exc,
    }


def get_weight_config(tipo_balanza: str, cap_max_kg: float, carga_elegida_kg: float = None):
    """
    Reglas puramente por capacidad:
      - cap ≤ 999 kg  → pesas de 20 kg
      - cap ≥ 1000 kg → pesas de 1000 kg, usuario elige carga (default 50%)
    """
    if cap_max_kg <= 999:
        pesa = 20
        carga_max = round(cap_max_kg * 0.5 / 20) * 20
        carga_max = max(carga_max, 20)
        return _build_config(pesa, carga_max)

    # 1000–2000 kg: pesas de 500 kg (permite pasos de 500, 1000, 1500, 2000)
    if cap_max_kg <= 2000:
        pesa = 500
        default_max = max(500, math.floor(cap_max_kg * 0.5 / 500) * 500)
        carga_max = carga_elegida_kg if carga_elegida_kg else default_max
        return _build_config(pesa, carga_max, user_chooses=True)

    # > 2000 kg: pesas de 1000 kg
    pesa = 1000
    default_max = max(1000, math.floor(cap_max_kg * 0.5 / 1000) * 1000)
    carga_max = carga_elegida_kg if carga_elegida_kg else default_max
    return _build_config(pesa, carga_max, user_chooses=True)


def _build_config(pesa_kg, carga_max_kg, user_chooses=False):
    n = max(1, round(carga_max_kg / pesa_kg))
    cargas = [pesa_kg * i for i in range(1, n + 1)]
    return {
        "pesa_kg": pesa_kg,
        "carga_max_kg": carga_max_kg,
        "linealidad_cargas": cargas,
        "excentricidad_carga": cargas[-1] if cargas else carga_max_kg,
        "user_chooses_load": user_chooses,
    }
