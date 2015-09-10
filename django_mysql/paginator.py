from django.core.paginator import Paginator


class FoundRowsPaginator(Paginator):

    def __init__(self, *args, **kwargs):
        super(FoundRowsPaginator, self).__init__(*args, **kwargs)
        if hasattr(self.object_list, 'sql_calc_found_rows') and not hasattr(self.object_list, 'found_rows'):
            self.object_list = self.object_list.sql_calc_found_rows()
            self.can_calc_found_rows = True
        else:
            self.can_calc_found_rows = False

    def _get_page(self, object_slice, *args, **kwargs):
        if hasattr(object_slice.__class__, 'found_rows'):
            if hasattr(self, 'found_rows'):
                object_slice.found_rows = self.found_rows  # disables this query
            else:
                list(object_slice)  # populate _result_cache
                self.found_rows = object_slice.found_rows
        return super(FoundRowsPaginator, self)._get_page(object_slice, *args, **kwargs)

    def _get_count(self):
        # Note - until we calculate found_rows, we disable some counting logic
        # by returning infinite
        if self.can_calc_found_rows:
            return getattr(self, 'found_rows', float('inf'))
        else:
            return super(FoundRowsPaginator, self)._get_count()

    count = property(_get_count)

    def _get_num_pages(self):
        # If self.count is disabled as above, disable more logic by assuming
        # there are infinite pages
        if self.count == float('inf'):
            return float('inf')
        else:
            return super(FoundRowsPaginator, self)._get_num_pages()

    num_pages = property(_get_num_pages)
