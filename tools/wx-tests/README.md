# wxQt regression tests

Small programs that check fixes in `patches/wxwidgets` against the desktop wxQt build
(`scripts/build-wxqt-desktop.sh`), with AddressSanitizer:

```
P=build/install/wxqt-desktop; source scripts/env.sh
clang++ -std=c++17 -g -fsanitize=address tools/wx-tests/tree_item_data_move.cpp -o /tmp/t \
    $($P/bin/wx-config --cxxflags) $($P/bin/wx-config --libs core,base) -Wl,-rpath,$P/lib
QT_QPA_PLATFORM=offscreen DYLD_FRAMEWORK_PATH=$QT_HOST_PATH/lib /tmp/t
```

- `tree_item_data_move.cpp` checks patch 0026. Moving a tree item's client data to another
  item and clearing the old one must keep the data alive. Before the patch this crashed in
  `dynamic_cast` (a use after free), as KiCad's DRC rule editor did when a rule was dragged
  (10.99ah crash, 2026-11-07).
