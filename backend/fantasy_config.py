"""Единая конфигурация помощника официального Dota Fantasy.

Здесь намеренно нет SQL и OpenDota-логики. После публикации нового
компендиума в большинстве случаев достаточно поменять этот файл:

* доступные показатели и их формулы;
* цвета/количество слотов для каждой роли;
* наличие и диапазон множителей;
* турниры, из которых строится форма игроков.

Парсер при этом хранит более широкий набор сырых показателей и компактный
JSON-снимок OpenDota, поэтому изменение правил не требует повторного
проектирования интерфейса или немедленной миграции под каждый новый счётчик.
"""

from __future__ import annotations


FANTASY_LEAGUES: dict[int, str] = {
    19785: "EWC 2026",
    19101: "BLAST SLAM VII",
    19099: "BLAST SLAM VI",
    19269: "DreamLeague S28",
    19696: "DreamLeague S29",
    19435: "PGL Wallachia S7",
    19543: "PGL Wallachia S8",
    19422: "ESL One Birmingham 2026",
}

# Значения OpenDota /proPlayers.fantasy_role.
OPENDOTA_FANTASY_ROLES: dict[int, str] = {
    1: "core",
    2: "support",
    4: "mid",
}

# Только fallback для редких игроков, которых ещё нет или неверно разметили
# в /proPlayers. Основной источник ролей — OpenDota, поэтому список пустой.
# Формат: account_id: "core" | "mid" | "support".
FANTASY_POSITION_OVERRIDES: dict[int, str] = {}


# field — имя среднего значения в /api/fantasy/players.
# formula — полностью декларативна: клиент не знает коэффициентов Valve.
FANTASY_METRICS: tuple[dict, ...] = (
    {
        "id": "kills",
        "field": "avg_kills",
        "label": "Убийства",
        "short_label": "K",
        "color": "red",
        "formula": {"type": "linear", "factor": 121},
    },
    {
        "id": "deaths",
        "field": "avg_deaths",
        "label": "Смерти",
        "short_label": "D",
        "color": "red",
        "formula": {"type": "inverse", "base": 1800, "factor": 180, "floor": 0},
    },
    {
        "id": "creep_score",
        "field": "avg_creep_score",
        "label": "Крипы",
        "short_label": "CS",
        "color": "green",
        "formula": {"type": "linear", "factor": 3},
    },
    {
        "id": "gpm",
        "field": "avg_gpm",
        "label": "Золото в минуту",
        "short_label": "GPM",
        "color": "green",
        "formula": {"type": "linear", "factor": 2},
    },
    {
        "id": "madstones",
        "field": "avg_madstones",
        "label": "Мэдстоуны",
        "short_label": "MS",
        "color": "green",
        "formula": {"type": "linear", "factor": 57},
    },
    {
        "id": "tower_kills",
        "field": "avg_tower_kills",
        "label": "Башни",
        "short_label": "TWR",
        "color": "red",
        "formula": {"type": "linear", "factor": 340},
    },
    {
        "id": "obs",
        "field": "avg_obs",
        "label": "Варды",
        "short_label": "OBS",
        "color": "blue",
        "formula": {"type": "linear", "factor": 113},
    },
    {
        "id": "camps",
        "field": "avg_camps",
        "label": "Стаки",
        "short_label": "STACK",
        "color": "green",
        "formula": {"type": "linear", "factor": 170},
    },
    {
        "id": "runes",
        "field": "avg_runes",
        "label": "Руны",
        "short_label": "RUNE",
        "color": "green",
        "formula": {"type": "linear", "factor": 121},
    },
    {
        "id": "watchers",
        "field": "avg_watchers",
        "label": "Смотрители",
        "short_label": "WATCH",
        "color": "blue",
        "formula": {"type": "linear", "factor": 90},
    },
    {
        "id": "smokes",
        "field": "avg_smokes",
        "label": "Смоки",
        "short_label": "SMOKE",
        "color": "blue",
        "formula": {"type": "linear", "factor": 283},
    },
    {
        "id": "roshan",
        "field": "avg_roshan_kills",
        "label": "Рошаны",
        "short_label": "ROSH",
        "color": "red",
        "formula": {"type": "linear", "factor": 850},
    },
    {
        "id": "teamfight",
        "field": "avg_teamfight",
        "label": "Участие в драках",
        "short_label": "TF",
        "color": "blue",
        "formula": {"type": "linear", "factor": 1895},
    },
    {
        "id": "stuns",
        "field": "avg_stuns",
        "label": "Контроль",
        "short_label": "STUN",
        "color": "blue",
        "formula": {"type": "linear", "factor": 15},
    },
    {
        "id": "tormentor",
        "field": "avg_tormentor_kills",
        "label": "Терзатели",
        "short_label": "TRM",
        "color": "red",
        "formula": {"type": "linear", "factor": 850},
    },
    {
        "id": "courier",
        "field": "avg_courier_kills",
        "label": "Курьеры",
        "short_label": "COURIER",
        "color": "green",
        "formula": {"type": "linear", "factor": 850},
    },
    {
        "id": "firstblood",
        "field": "avg_firstblood",
        "label": "Первая кровь",
        "short_label": "FB",
        "color": "red",
        "formula": {"type": "linear", "factor": 1700},
    },
)


FANTASY_ROLES: tuple[dict, ...] = (
    {
        "id": "core",
        "label": "Коры",
        "slots": (
            {"color": "red", "default_metric": "kills"},
            {"color": "green", "default_metric": "creep_score"},
            {"color": "red", "default_metric": "tower_kills"},
            {"color": "green", "default_metric": "gpm"},
            {"color": "red", "default_metric": "roshan"},
        ),
    },
    {
        "id": "mid",
        "label": "Мид",
        "slots": (
            {"color": "red", "default_metric": "kills"},
            {"color": "blue", "default_metric": "teamfight"},
            {"color": "green", "default_metric": "gpm"},
            {"color": "red", "default_metric": "tower_kills"},
            {"color": "green", "default_metric": "runes"},
        ),
    },
    {
        "id": "support",
        "label": "Саппорты",
        "slots": (
            {"color": "blue", "default_metric": "obs"},
            {"color": "green", "default_metric": "camps"},
            {"color": "blue", "default_metric": "smokes"},
            {"color": "green", "default_metric": "courier"},
            {"color": "blue", "default_metric": "stuns"},
        ),
    },
)


def get_fantasy_config() -> dict:
    """Вернуть JSON-совместимую схему экрана и расчёта."""
    return {
        "ruleset_id": "ti_fantasy_current",
        "mechanics": {
            # Если Valve уберёт эмблемы, false скрывает конструктор, а рейтинг
            # продолжает работать на role.default_metrics/slots.
            "slots_enabled": True,
            "multiplier": {
                "enabled": True,
                "values": [1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
                "default": 1.0,
            },
        },
        "roles": list(FANTASY_ROLES),
        "metrics": list(FANTASY_METRICS),
        "tournaments": [
            {"id": league_id, "label": label}
            for league_id, label in FANTASY_LEAGUES.items()
        ],
    }
