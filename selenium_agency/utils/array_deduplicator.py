
from .utils import objects_equal

class ArrayDeduplicator:

  def __init__(self):
      pass

  def _filter_items(self, target, based_on_items, target_id_keyword, base_id_keyword, attributes_compare_callback):
    result = []
    counter = 1
    for item in target:
        print(f"\rDeduplicating load: {counter} / {len(target)}", end='', flush=True)
        counter += 1
        exists_in_based_on = False
        for base_item in based_on_items:
            if objects_equal(item, base_item, attributes_compare_callback, target_id_keyword, base_id_keyword):
                exists_in_based_on = True
                break

        if not exists_in_based_on:
            result.append(item)

    # Add a final newline after the loop is complete
    print()
    return result

  def apply_deduplication(self, target, based_on, target_id_keyword, base_id_keyword, attributes_compare_callback=None):
      if not target:
          print("Warning: 'to' array is empty. Returning an empty array.")
          return []

      if not based_on:
          print("Warning: 'based_on' array is empty. Returning a copy of 'to' array.")
          return target.copy()

      # Use comparison-based filtering which works with any input types
      return self._filter_items(target, based_on, target_id_keyword, base_id_keyword, attributes_compare_callback)