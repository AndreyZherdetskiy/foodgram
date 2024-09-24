from rest_framework.pagination import PageNumberPagination

from api.constants import PAGINATION_MAX_PAGE_SIZE, PAGINATION_PAGE_SIZE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = PAGINATION_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = PAGINATION_MAX_PAGE_SIZE
