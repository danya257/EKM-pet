"""Inclusion tags для дизайн-системы Vetka."""
from django import template

register = template.Library()


@register.inclusion_tag('partials/stars.html')
def stars(value):
    """{% stars vet.rating %} → 5 SVG-звёзд с заливкой пропорционально оценке."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0
    v = max(0.0, min(5.0, v))
    parts = []
    for i in range(1, 6):
        # 1.0 — полная, 0.5 — половина, 0 — пустая
        if v >= i:
            parts.append('full')
        elif v >= i - 0.5:
            parts.append('half')
        else:
            parts.append('empty')
    return {'parts': parts, 'value': v}


@register.simple_tag
def icon(name, cls=''):
    """{% icon "search" "icon-lg" %} → <svg class="icon icon-lg"><use href="#i-search"/></svg>"""
    cls_attr = f'icon {cls}'.strip()
    from django.utils.safestring import mark_safe
    return mark_safe(f'<svg class="{cls_attr}"><use href="#i-{name}"/></svg>')
