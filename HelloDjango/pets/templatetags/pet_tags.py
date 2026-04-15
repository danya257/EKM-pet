# pets/templatetags/pet_tags.py
from django import template

register = template.Library()

@register.inclusion_tag('pets/animal_icon.html')
def animal_icon(species):
    """
    Рендерит анимированную SVG-иконку для вида животного.
    Использование: {% animal_icon pet.species %}
    """
    return {'species': species}