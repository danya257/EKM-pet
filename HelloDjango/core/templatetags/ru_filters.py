from django import template

register = template.Library()


@register.filter
def plural_ru(value, forms):
    """
    Русская плюрализация: {{ count|plural_ru:"отзыв,отзыва,отзывов" }}.

    forms — три формы через запятую:
        - 1 (1, 21, 31…)             → форма 0
        - 2-4 (22, 23, 24, 32…)      → форма 1
        - 5-20, 0 (5, 11, 25…)       → форма 2
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return ''
    parts = [p.strip() for p in str(forms).split(',')]
    if len(parts) != 3:
        return parts[-1] if parts else ''
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 19:
        return parts[2]
    if n1 == 1:
        return parts[0]
    if 2 <= n1 <= 4:
        return parts[1]
    return parts[2]
