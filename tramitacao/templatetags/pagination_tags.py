from django import template

register = template.Library()

@register.filter
def get_pagination_range(page_obj):
    """
    Gera uma lista inteligente de páginas com reticências para o Paginator do Django.
    Ex: [1, '...', 4, 5, 6, '...', 10]
    """
    current = page_obj.number
    total = page_obj.paginator.num_pages
    
    if total <= 7:
        return range(1, total + 1)
        
    pages = []
    
    # Sempre mostra a primeira e segunda, ou perto da atual
    if current > 4:
        pages.append(1)
        pages.append('...')
        
    start = max(1, current - 2)
    end = min(total, current + 2)
    
    for i in range(start, end + 1):
        pages.append(i)
        
    if current < total - 3:
        pages.append('...')
        pages.append(total)
        
    return pages