# Menu Modules

Central location for EvMenu node definitions.

- Each menu lives in its own module in this package.
- Commands start menus by passing the module object to `EnhancedEvMenu`.
- Menu text usually includes its own A/B choice lines, so `show_options` defaults to `False`.
- Theming knobs like `border_color` and `prompt_color` can be tweaked per menu.
