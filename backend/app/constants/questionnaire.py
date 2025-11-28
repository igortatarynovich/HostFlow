# backend/app/constants/questionnaire.py
QUESTIONNAIRE_TEMPLATE = {
    "version": 1,
    "title": "Скрининг водитель",
    "sections": [
        {
            "key": "base",
            "title": "База",
            "questions": [
                {
                    "key": "license_cat",
                    "text": "Категория прав (C/CE)",
                    "type": "checkbox",
                    "options": [
                        {"key": "c", "label": "C", "points": 5},
                        {"key": "ce", "label": "CE", "points": 10},
                    ],
                    "max_select": 2,
                },
                {
                    "key": "intl_passport",
                    "text": "Загранпаспорт",
                    "type": "checkbox",
                    "options": [
                        {"key": "have", "label": "Есть", "points": 10},
                        {"key": "no", "label": "Нет", "points": 0},
                    ],
                    "max_select": 1,
                },
            ],
        },
        {
            "key": "experience",
            "title": "Опыт",
            "questions": [
                {
                    "key": "years_truck",
                    "text": "Опыт на грузовике (лет)",
                    "type": "scale",
                    "min": 0,
                    "max": 20,
                    "points_per_unit": 2,
                },
                {
                    "key": "eu_routes",
                    "text": "Опыт по ЕС",
                    "type": "checkbox",
                    "options": [
                        {"key": "have", "label": "Есть", "points": 10},
                        {"key": "no", "label": "Нет", "points": 0},
                    ],
                    "max_select": 1,
                },
            ],
        },
    ],
    "thresholds": {"pass": 20, "maybe": 12},
}
