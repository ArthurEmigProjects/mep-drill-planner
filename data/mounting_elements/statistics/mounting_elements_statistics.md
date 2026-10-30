# Mounting-element statistics

Generated 30 October 2026, 08:04 CET from data/mounting_elements/products.json (schema version 1) and data/inventory/zenodo_duplex_mountable.json. Dataset: DuplexModel+MEP (Teclaw, Wojciech, 2024), DOI 10.5281/zenodo.10610773, CC BY 4.0.

Figures are counts, shares and descriptive statistics of fields that are actually stored. A null load, spacing or material stays empty. An element can match more than one clamp, so product-hit totals are not a partition of the element count. A system assignment total can exceed the element count when one element sits in more than one system. Coverage below uses substrate none, so concrete anchors are not counted as matches. The architecture ceilings are gypsum under timber joists.


## Headline figures

| measure | value |
| --- | --- |
| products | 23 |
| guidance records | 3 |
| manufacturers | 6 |
| primary products | 18 |
| companion products | 5 |
| inventory size groups | 98 |
| inventory elements | 1163 |
| elements matched on a published size | 777 |
| elements matched with an assumption | 290 |
| elements unmatched | 96 |
| share matched on a published size | 66.8% |
| share matched with an assumption | 24.9% |
| share unmatched | 8.3% |
| pipe segment length, m | 303.832 |
| duct segment length, m | 118.376 |
| models | 3 |


## Products by manufacturer

Each product counts once. Share is the share of the catalogue, not of the building.

| manufacturer | products | share | primary | companion | with load | load empty | element types |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hilti | 6 | 26.1% | 3 | 3 | 3 | 3 | channel, pipe, threaded_rod |
| Kermi | 1 | 4.3% | 1 | 0 | 0 | 1 | radiator |
| Müpro | 3 | 13.0% | 3 | 0 | 0 | 3 | pipe |
| Sikla | 3 | 13.0% | 3 | 0 | 3 | 0 | duct_rectangular, duct_round |
| Walraven | 2 | 8.7% | 2 | 0 | 0 | 2 | pipe |
| fischer | 8 | 34.8% | 6 | 2 | 7 | 1 | ceiling_anchor, pipe |


## Products by product line

| product line | manufacturer | products | share | roles | element types |
| --- | --- | --- | --- | --- | --- |
| FRS Plus | fischer | 4 | 17.4% | primary | pipe |
| MP-MI | Hilti | 3 | 13.0% | primary | pipe |
| OPTIMAL | Müpro | 3 | 13.0% | primary | pipe |
| AM | Hilti | 2 | 8.7% | companion | threaded_rod |
| EA II | fischer | 2 | 8.7% | companion | ceiling_anchor |
| LUW | Sikla | 2 | 8.7% | primary | duct_rectangular |
| BISMAT 2000 | Walraven | 1 | 4.3% | primary | pipe |
| BISMAT KSB 2 | Walraven | 1 | 4.3% | primary | pipe |
| FRS A2 | fischer | 1 | 4.3% | primary | pipe |
| FRS-L Universal | fischer | 1 | 4.3% | primary | pipe |
| MQ | Hilti | 1 | 4.3% | companion | channel |
| PLU 2G-N m.E. | Sikla | 1 | 4.3% | primary | duct_round |
| Wandkonsole variabel | Kermi | 1 | 4.3% | primary | radiator |


## Products by element type

duct_flex is listed even when the count is zero: the catalogue has no flex-duct hanger. A product with several element types would be counted in each column of the cross table and once in this table per type.

| element type | products | share of catalogue | primary | companion | with OD window | with nominal diameter | with load |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pipe | 14 | 60.9% | 14 | 0 | 14 | 0 | 8 |
| duct_round | 1 | 4.3% | 1 | 0 | 0 | 1 | 1 |
| duct_rectangular | 2 | 8.7% | 2 | 0 | 0 | 0 | 2 |
| duct_flex | 0 | 0.0% | 0 | 0 | 0 | 0 | 0 |
| radiator | 1 | 4.3% | 1 | 0 | 0 | 0 | 0 |
| threaded_rod | 2 | 8.7% | 0 | 2 | 0 | 0 | 0 |
| channel | 1 | 4.3% | 0 | 1 | 0 | 0 | 0 |
| ceiling_anchor | 2 | 8.7% | 0 | 2 | 0 | 0 | 2 |


## Manufacturer by element type

| manufacturer | pipe | duct_round | duct_rectangular | duct_flex | radiator | threaded_rod | channel | ceiling_anchor | products |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hilti | 3 | 0 | 0 | 0 | 0 | 2 | 1 | 0 | 6 |
| Kermi | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| Müpro | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Sikla | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 3 |
| Walraven | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| fischer | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 |
| all | 14 | 1 | 2 | 0 | 1 | 2 | 1 | 2 | 23 |


## Products by role

| role | products | share | cumulative share |
| --- | --- | --- | --- |
| primary | 18 | 78.3% | 78.3% |
| companion | 5 | 21.7% | 100.0% |


## Field completeness

Filled means the JSON value is not null and, for a list, not empty. max_support_spacing is null on every product: published spacing lives in guidance.

| field | filled | empty | filled share |
| --- | --- | --- | --- |
| product_line | 23 | 0 | 100.0% |
| article_number | 23 | 0 | 100.0% |
| outer_diameter_mm | 14 | 9 | 60.9% |
| nominal_diameter_mm | 1 | 22 | 4.3% |
| connection_threads | 22 | 1 | 95.7% |
| load_rating | 13 | 10 | 56.5% |
| max_support_spacing | 0 | 23 | 0.0% |
| anchor | 3 | 20 | 13.0% |
| assumptions | 3 | 20 | 13.0% |
| notes | 23 | 0 | 100.0% |
| sources | 23 | 0 | 100.0% |

Article numbers: 23 stored, 23 distinct. Product ids: 23 stored, 23 distinct.


## Connection threads

A clamp with M8/M10 is counted under both threads. The share is the share of catalogue products that include the thread, so the column can sum to more than 100%.

| thread | products | share of catalogue |
| --- | --- | --- |
| M10 | 19 | 82.6% |
| M8 | 15 | 65.2% |
| M12 | 4 | 17.4% |

Products with an empty connection_threads list: 1 of 23.

| thread combination | role | products | share of catalogue |
| --- | --- | --- | --- |
| (none) | primary | 1 | 4.3% |
| M10 | companion | 2 | 8.7% |
| M10 | primary | 1 | 4.3% |
| M10+M12 | primary | 3 | 13.0% |
| M12 | companion | 1 | 4.3% |
| M8 | companion | 2 | 8.7% |
| M8+M10 | primary | 13 | 56.5% |


## Pipe-clamp windows

| id | manufacturer | article | min mm | max mm | span mm | threads | load kN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fischer-frs-l-539443 | fischer | 539443 | 8 | 11 | 3 | M8, M10 | 0.7 |
| fischer-frs-plus-079440 | fischer | 079440 | 12 | 15 | 3 | M8, M10 | 0.8 |
| muepro-optimal-119866 | Müpro | 119866 | 13 | 15 | 2 | M8, M10 |  |
| fischer-frs-plus-079441 | fischer | 079441 | 15 | 19 | 4 | M8, M10 | 0.8 |
| hilti-mp-mi-20843 | Hilti | 20843 | 15 | 19 | 4 | M10, M12 | 1.8 |
| muepro-optimal-119862 | Müpro | 119862 | 19 | 24 | 5 | M8, M10 |  |
| fischer-frs-plus-079442 | fischer | 079442 | 20 | 24 | 4 | M8, M10 | 0.8 |
| hilti-mp-mi-20845 | Hilti | 20845 | 20 | 25 | 5 | M10, M12 | 1.8 |
| fischer-frs-plus-079445 | fischer | 079445 | 40 | 45 | 5 | M8, M10 | 1 |
| hilti-mp-mi-20851 | Hilti | 20851 | 40 | 45 | 5 | M10, M12 | 1.8 |
| muepro-optimal-119858 | Müpro | 119858 | 41 | 44 | 3 | M8, M10 |  |
| walraven-bismat-2000-3403105 | Walraven | 3403105 | 100 | 105 | 5 | M8, M10 |  |
| walraven-bismat-ksb2-3396105 | Walraven | 3396105 | 100 | 105 | 5 | M8, M10 |  |
| fischer-frs-a2-064697 | fischer | 064697 | 102 | 116 | 14 | M10 |  |

Span is max minus min of the published window. Load kN converts N by dividing by 1000 and leaves a cell empty when the source published no load. The definitions still differ by product and are not one allowable-load population.


## Descriptive statistics of pipe-clamp windows

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| window min, mm | 14 | 545 | 8 | 102 | 94 | 38.929 | 20 | 35.145 | 15 | 40.75 |
| window max, mm | 14 | 612 | 11 | 116 | 105 | 43.714 | 24.5 | 37.012 | 19 | 45 |
| window span, mm | 14 | 67 | 2 | 14 | 12 | 4.786 | 4.5 | 2.833 | 3.25 | 5 |
| published load of these clamps, kN | 8 | 9.5 | 0.7 | 1.8 | 1.1 | 1.188 | 0.9 | 0.514 | 0.8 | 1.8 |


## Overlapping pipe-clamp windows

Two windows overlap when their intervals meet within 0.02 mm, the same tolerance the mapper uses. A zero-width overlap is a shared boundary, so an outside diameter equal to that boundary matches both clamps.

| article A | article B | overlap min mm | overlap max mm | overlap width mm |
| --- | --- | --- | --- | --- |
| 119866 | 079440 | 13 | 15 | 2 |
| 079440 | 079441 | 15 | 15 | 0 |
| 079440 | 20843 | 15 | 15 | 0 |
| 079441 | 20843 | 15 | 19 | 4 |
| 119866 | 079441 | 15 | 15 | 0 |
| 119866 | 20843 | 15 | 15 | 0 |
| 119862 | 079441 | 19 | 19 | 0 |
| 119862 | 20843 | 19 | 19 | 0 |
| 079442 | 20845 | 20 | 24 | 4 |
| 119862 | 079442 | 20 | 24 | 4 |
| 119862 | 20845 | 20 | 24 | 4 |
| 079445 | 20851 | 40 | 45 | 5 |
| 119858 | 079445 | 41 | 44 | 3 |
| 119858 | 20851 | 41 | 44 | 3 |
| 3396105 | 3403105 | 100 | 105 | 5 |
| 064697 | 3396105 | 102 | 105 | 3 |
| 064697 | 3403105 | 102 | 105 | 3 |

Overlapping or boundary-touching pairs: 17.


## Merged clamp coverage and holes

| covered from mm | covered to mm | width mm |
| --- | --- | --- |
| 8 | 11 | 3 |
| 12 | 25 | 13 |
| 40 | 45 | 5 |
| 100 | 116 | 16 |

| hole after mm | hole before mm | width mm |
| --- | --- | --- |
| 11 | 12 | 1 |
| 25 | 40 | 15 |
| 45 | 100 | 55 |

Depth is how many primary pipe clamps the mapper returns for each integer millimetre from the lowest published minimum to the highest published maximum.


## Descriptive statistics of integer clamp depth

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clamps covering each integer mm | 109 | 81 | 0 | 4 | 4 | 0.743 | 0 | 1.117 | 0 | 1 |

| clamps at that mm | integer mm count | share of the scanned mm | cumulative share |
| --- | --- | --- | --- |
| 0 | 68 | 62.4% | 62.4% |
| 1 | 17 | 15.6% | 78.0% |
| 3 | 14 | 12.8% | 90.8% |
| 2 | 9 | 8.3% | 99.1% |
| 4 | 1 | 0.9% | 100.0% |

| uncovered integers from mm | uncovered integers to mm | count of integers |
| --- | --- | --- |
| 26 | 39 | 14 |
| 46 | 99 | 54 |


## Clamp depth at each integer millimetre

| mm | matching clamps | product ids |
| --- | --- | --- |
| 8 | 1 | fischer-frs-l-539443 |
| 9 | 1 | fischer-frs-l-539443 |
| 10 | 1 | fischer-frs-l-539443 |
| 11 | 1 | fischer-frs-l-539443 |
| 12 | 1 | fischer-frs-plus-079440 |
| 13 | 2 | muepro-optimal-119866, fischer-frs-plus-079440 |
| 14 | 2 | muepro-optimal-119866, fischer-frs-plus-079440 |
| 15 | 4 | muepro-optimal-119866, fischer-frs-plus-079440, fischer-frs-plus-079441, hilti-mp-mi-20843 |
| 16 | 2 | fischer-frs-plus-079441, hilti-mp-mi-20843 |
| 17 | 2 | fischer-frs-plus-079441, hilti-mp-mi-20843 |
| 18 | 2 | fischer-frs-plus-079441, hilti-mp-mi-20843 |
| 19 | 3 | muepro-optimal-119862, fischer-frs-plus-079441, hilti-mp-mi-20843 |
| 20 | 3 | muepro-optimal-119862, fischer-frs-plus-079442, hilti-mp-mi-20845 |
| 21 | 3 | muepro-optimal-119862, fischer-frs-plus-079442, hilti-mp-mi-20845 |
| 22 | 3 | muepro-optimal-119862, fischer-frs-plus-079442, hilti-mp-mi-20845 |
| 23 | 3 | muepro-optimal-119862, fischer-frs-plus-079442, hilti-mp-mi-20845 |
| 24 | 3 | muepro-optimal-119862, fischer-frs-plus-079442, hilti-mp-mi-20845 |
| 25 | 1 | hilti-mp-mi-20845 |
| 26 | 0 |  |
| 27 | 0 |  |
| 28 | 0 |  |
| 29 | 0 |  |
| 30 | 0 |  |
| 31 | 0 |  |
| 32 | 0 |  |
| 33 | 0 |  |
| 34 | 0 |  |
| 35 | 0 |  |
| 36 | 0 |  |
| 37 | 0 |  |
| 38 | 0 |  |
| 39 | 0 |  |
| 40 | 2 | fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 41 | 3 | muepro-optimal-119858, fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 42 | 3 | muepro-optimal-119858, fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 43 | 3 | muepro-optimal-119858, fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 44 | 3 | muepro-optimal-119858, fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 45 | 2 | fischer-frs-plus-079445, hilti-mp-mi-20851 |
| 46 | 0 |  |
| 47 | 0 |  |
| 48 | 0 |  |
| 49 | 0 |  |
| 50 | 0 |  |
| 51 | 0 |  |
| 52 | 0 |  |
| 53 | 0 |  |
| 54 | 0 |  |
| 55 | 0 |  |
| 56 | 0 |  |
| 57 | 0 |  |
| 58 | 0 |  |
| 59 | 0 |  |
| 60 | 0 |  |
| 61 | 0 |  |
| 62 | 0 |  |
| 63 | 0 |  |
| 64 | 0 |  |
| 65 | 0 |  |
| 66 | 0 |  |
| 67 | 0 |  |
| 68 | 0 |  |
| 69 | 0 |  |
| 70 | 0 |  |
| 71 | 0 |  |
| 72 | 0 |  |
| 73 | 0 |  |
| 74 | 0 |  |
| 75 | 0 |  |
| 76 | 0 |  |
| 77 | 0 |  |
| 78 | 0 |  |
| 79 | 0 |  |
| 80 | 0 |  |
| 81 | 0 |  |
| 82 | 0 |  |
| 83 | 0 |  |
| 84 | 0 |  |
| 85 | 0 |  |
| 86 | 0 |  |
| 87 | 0 |  |
| 88 | 0 |  |
| 89 | 0 |  |
| 90 | 0 |  |
| 91 | 0 |  |
| 92 | 0 |  |
| 93 | 0 |  |
| 94 | 0 |  |
| 95 | 0 |  |
| 96 | 0 |  |
| 97 | 0 |  |
| 98 | 0 |  |
| 99 | 0 |  |
| 100 | 2 | walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 101 | 2 | walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 102 | 3 | fischer-frs-a2-064697, walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 103 | 3 | fischer-frs-a2-064697, walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 104 | 3 | fischer-frs-a2-064697, walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 105 | 3 | fischer-frs-a2-064697, walraven-bismat-ksb2-3396105, walraven-bismat-2000-3403105 |
| 106 | 1 | fischer-frs-a2-064697 |
| 107 | 1 | fischer-frs-a2-064697 |
| 108 | 1 | fischer-frs-a2-064697 |
| 109 | 1 | fischer-frs-a2-064697 |
| 110 | 1 | fischer-frs-a2-064697 |
| 111 | 1 | fischer-frs-a2-064697 |
| 112 | 1 | fischer-frs-a2-064697 |
| 113 | 1 | fischer-frs-a2-064697 |
| 114 | 1 | fischer-frs-a2-064697 |
| 115 | 1 | fischer-frs-a2-064697 |
| 116 | 1 | fischer-frs-a2-064697 |


## Published loads

kN is the stored value when the unit is already kN, and the stored value divided by 1000 when the unit is N. Empty load cells are excluded from the descriptive rows. Kinds are kept apart because a recommended static load, a Nutzlast and an anchor Fzul are not interchangeable.

| id | manufacturer | element type | value | unit | kN | kind |
| --- | --- | --- | --- | --- | --- | --- |
| fischer-frs-l-539443 | fischer | pipe | 0.7 | kN | 0.7 | max. recommended static load, centric tension |
| fischer-frs-plus-079440 | fischer | pipe | 0.8 | kN | 0.8 | max. recommended static load, centric tension |
| fischer-frs-plus-079441 | fischer | pipe | 0.8 | kN | 0.8 | max. recommended static load, centric tension |
| fischer-frs-plus-079442 | fischer | pipe | 0.8 | kN | 0.8 | max. recommended static load, centric tension |
| fischer-frs-plus-079445 | fischer | pipe | 1 | kN | 1 | max. recommended static load, centric tension |
| hilti-mp-mi-20843 | Hilti | pipe | 1800 | N | 1.8 | maximum load F, ambient, for the 15–64 mm band of MP-MI series G |
| hilti-mp-mi-20845 | Hilti | pipe | 1800 | N | 1.8 | maximum load F, ambient, for the 15–64 mm band of MP-MI series G |
| hilti-mp-mi-20851 | Hilti | pipe | 1800 | N | 1.8 | maximum load F, ambient, for the 15–64 mm band of MP-MI series G |
| sikla-plu-2g-199893 | Sikla | duct_round | 0.8 | kN | 0.8 | zulässige Nutzlast for types 71–200 |
| sikla-luw-sl-189893 | Sikla | duct_rectangular | 0.8 | kN | 0.8 | Nennlast |
| sikla-luw-sz-189902 | Sikla | duct_rectangular | 0.8 | kN | 0.8 | Nennlast |
| fischer-ea-ii-m8-532231 | fischer | ceiling_anchor | 1.4 | kN | 1.4 | permissible load Fzul of one anchor for redundant non-structural use in concrete C20/25 to C50/60 |
| fischer-ea-ii-m10-532232 | fischer | ceiling_anchor | 1.9 | kN | 1.9 | permissible load Fzul of one anchor for redundant non-structural use in concrete C20/25 to C50/60 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all published loads converted to kN | 13 | 15.2 | 0.7 | 1.9 | 1.2 | 1.169 | 0.8 | 0.487 | 0.8 | 1.8 |
| Nennlast | 2 | 1.6 | 0.8 | 0.8 | 0 | 0.8 | 0.8 | 0 |  |  |
| max. recommended static load, centric tension | 5 | 4.1 | 0.7 | 1 | 0.3 | 0.82 | 0.8 | 0.11 | 0.8 | 0.8 |
| maximum load F, ambient, for the 15–64 mm band of MP-MI series G | 3 | 5.4 | 1.8 | 1.8 | 0 | 1.8 | 1.8 | 0 |  |  |
| permissible load Fzul of one anchor for redundant non-structural use in concrete C20/25 to C50/60 | 2 | 3.3 | 1.4 | 1.9 | 0.5 | 1.65 | 1.65 | 0.354 |  |  |
| zulässige Nutzlast for types 71–200 | 1 | 0.8 | 0.8 | 0.8 | 0 | 0.8 | 0.8 |  |  |  |

| id | manufacturer | element type | article |
| --- | --- | --- | --- |
| muepro-optimal-119866 | Müpro | pipe | 119866 |
| muepro-optimal-119862 | Müpro | pipe | 119862 |
| muepro-optimal-119858 | Müpro | pipe | 119858 |
| fischer-frs-a2-064697 | fischer | pipe | 064697 |
| walraven-bismat-ksb2-3396105 | Walraven | pipe | 3396105 |
| walraven-bismat-2000-3403105 | Walraven | pipe | 3403105 |
| hilti-mq-41-3-369596 | Hilti | channel | 369596 |
| hilti-rod-am8-339793 | Hilti | threaded_rod | 339793 |
| hilti-rod-am10-339795 | Hilti | threaded_rod | 339795 |
| kermi-console-zb02870003 | Kermi | radiator | ZB02870003 |

Products with no published load in the database: 10 of 23.


## Anchors stored on products

| id | manufacturer | anchor type | thread | substrate | included fixings | load kN |
| --- | --- | --- | --- | --- | --- | --- |
| fischer-ea-ii-m8-532231 | fischer | hammer-set internally threaded anchor | M8 | concrete |  | 1.4 |
| fischer-ea-ii-m10-532232 | fischer | hammer-set internally threaded anchor | M10 | concrete |  | 1.9 |
| kermi-console-zb02870003 | Kermi | wall plug and screw, included with the console set |  | wall | 2 screws 8×60 mm, 2 plugs 10×60 mm, 2 washers |  |

| substrate | products | share of anchored products | cumulative share |
| --- | --- | --- | --- |
| concrete | 2 | 66.7% | 66.7% |
| wall | 1 | 33.3% | 100.0% |


## Guidance records

| id | applies to | rows | rows flagged table_row | sources | note characters |
| --- | --- | --- | --- | --- | --- |
| copper-tube-spacing-din1988-2-as-cited | pipe | 12 |  | 2 | 610 |
| lindab-duct-suspension-spacing | duct_round, duct_rectangular | 6 | 4 | 1 | 292 |
| en-12236-duct-support-strength | duct_round, duct_rectangular, duct_flex | 0 |  | 2 | 557 |


## Guidance rows: copper-tube-spacing-din1988-2-as-cited

Both catalogues print this as Richtwerte for copper and stainless tube and attribute it to DIN 1988 Teil 2. The standard text was not read for this database. The column copied here is straight length (Stangenrohr). The same IBP table gives shorter distances for copper coil (Ringrohr), for example 0.7–0.9 m at 15 mm, and those are not applied. No vertical-stack column is in this table. A row is offered for a modeled pipe only when the outside diameter is within 0.5 mm of a listed value, and only with the explicit assumption that the unnamed IFC material is the copper or stainless tube the table is about.

| outer_diameter_mm | horizontal_m | form |
| --- | --- | --- |
| 12 | 1.25 | stangenrohr |
| 15 | 1.25 | stangenrohr |
| 18 | 1.5 | stangenrohr |
| 22 | 2 | stangenrohr |
| 28 | 2.25 | stangenrohr |
| 35 | 2.75 | stangenrohr |
| 42 | 3 | stangenrohr |
| 54 | 3.5 | stangenrohr |
| 64 | 4 | stangenrohr |
| 76.1 | 4.25 | stangenrohr |
| 88.9 | 4.75 | stangenrohr |
| 108 | 5 | stangenrohr |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| horizontal spacing, m | 12 | 35.5 | 1.25 | 5 | 3.75 | 2.958 | 2.875 | 1.343 | 1.875 | 4.062 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| table outside diameter, mm | 12 | 563 | 12 | 108 | 96 | 46.917 | 38.5 | 31.488 | 21 | 67.025 |


## Guidance rows: lindab-duct-suspension-spacing

Swedish Lindab suspension guide, widely used for European spiral and rectangular duct. Vertical runs in the same section are limited to 3 m for both shapes. The size-table rows above are the uninsulated, no-fire-class case. Insulated and fire-rated tables in the same document are not copied.

| shape | diameter_mm | horizontal_m | table_row | conditions | width_mm | height_mm |
| --- | --- | --- | --- | --- | --- | --- |
| round | 150 | 3 | yes | uninsulated circular duct, no fire class; recommended spacing 3.0 m across the listed hanger types |  |  |
| rectangular |  | 2.4 | yes | uninsulated rectangular duct, no fire class | 200 | 150 |
| rectangular |  | 2.4 | yes | uninsulated rectangular duct, no fire class | 300 | 150 |
| rectangular |  | 2.4 | yes | uninsulated rectangular duct, no fire class | 300 | 300 |
| rectangular |  | 2.4 | no | stated maximum hanger spacing for horizontal rectangular duct in that section, because more than one duct joint between hangers is considered unsuitable. 150×150 mm is not a row in the size table, which starts at width 200 mm. |  |  |
| round |  | 3 | no | stated maximum hanger spacing for horizontal circular duct in that section |  |  |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| horizontal spacing of table_row true, m | 4 | 10.2 | 2.4 | 3 | 0.6 | 2.55 | 2.4 | 0.3 | 2.4 | 2.55 |


## Guidance rows: en-12236-duct-support-strength

DIN EN 12236:2002 (EN 12236:2002) specifies strength of supports for sheet-metal ductwork of any shape. It does not publish a spacing table. From the preview of the EN text: the fixing into the structure needs a safety factor of at least 3 on the calculated load; vertical members and the joint to the horizontal member need a safety factor of at least 1.5 against yield; horizontal-member deflection must not exceed 0.4 % of the distance between the vertical fixings. Fire loading is outside the standard's scope. No spacing number is derived from it here.

This record has no numeric rows.


## Inventory by model

| model | file | schema | elements | share of elements | groups | recorded length m | elements matched | elements with assumption | elements unmatched | element matched share | element unmatched share | groups matched | groups with assumption | groups unmatched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| piping | zenodo-duplex-piping.ifc | IFC2X3 | 463 | 39.8% | 41 | 108.565 | 449 | 0 | 14 | 97.0% | 3.0% | 37 | 0 | 4 |
| ventilation | zenodo-duplex-ventilation.ifc | IFC2X3 | 374 | 32.2% | 40 | 118.376 | 20 | 274 | 80 | 5.3% | 21.4% | 3 | 29 | 8 |
| heating_and_cooling | HeatingAndCooling.ifc | IFC2X3 | 326 | 28.0% | 17 | 195.267 | 308 | 16 | 2 | 94.5% | 0.6% | 15 | 1 | 1 |


## Elements by kind

| kind | elements | share of elements | cumulative share |
| --- | --- | --- | --- |
| pipe_fitting | 386 | 33.2% | 33.2% |
| pipe_segment | 357 | 30.7% | 63.9% |
| duct_fitting | 156 | 13.4% | 77.3% |
| duct_segment | 126 | 10.8% | 88.1% |
| air_terminal | 40 | 3.4% | 91.6% |
| duct_flex | 36 | 3.1% | 94.7% |
| radiator | 16 | 1.4% | 96.0% |
| pipe_accessory | 14 | 1.2% | 97.2% |
| duct_accessory | 14 | 1.2% | 98.5% |
| sanitary_fixture | 12 | 1.0% | 99.5% |
| water_heater | 2 | 0.2% | 99.7% |
| air_handling_unit | 2 | 0.2% | 99.8% |
| stove | 2 | 0.2% | 100.0% |


## Size groups by kind

| kind | groups | share of groups | cumulative share |
| --- | --- | --- | --- |
| pipe_fitting | 40 | 40.8% | 40.8% |
| duct_fitting | 25 | 25.5% | 66.3% |
| pipe_segment | 9 | 9.2% | 75.5% |
| duct_segment | 5 | 5.1% | 80.6% |
| air_terminal | 4 | 4.1% | 84.7% |
| pipe_accessory | 3 | 3.1% | 87.8% |
| sanitary_fixture | 3 | 3.1% | 90.8% |
| duct_accessory | 3 | 3.1% | 93.9% |
| duct_flex | 2 | 2.0% | 95.9% |
| water_heater | 1 | 1.0% | 96.9% |
| air_handling_unit | 1 | 1.0% | 98.0% |
| radiator | 1 | 1.0% | 99.0% |
| stove | 1 | 1.0% | 100.0% |

| kind | piping | ventilation | heating_and_cooling | elements |
| --- | --- | --- | --- | --- |
| air_handling_unit | 0 | 2 | 0 | 2 |
| air_terminal | 0 | 40 | 0 | 40 |
| duct_accessory | 0 | 14 | 0 | 14 |
| duct_fitting | 0 | 156 | 0 | 156 |
| duct_flex | 0 | 36 | 0 | 36 |
| duct_segment | 0 | 126 | 0 | 126 |
| pipe_accessory | 10 | 0 | 4 | 14 |
| pipe_fitting | 233 | 0 | 153 | 386 |
| pipe_segment | 206 | 0 | 151 | 357 |
| radiator | 0 | 0 | 16 | 16 |
| sanitary_fixture | 12 | 0 | 0 | 12 |
| stove | 0 | 0 | 2 | 2 |
| water_heater | 2 | 0 | 0 | 2 |


## Elements by IFC class

| IFC class | elements | share of elements | cumulative share |
| --- | --- | --- | --- |
| IfcFlowFitting | 526 | 45.2% | 45.2% |
| IfcFlowSegment | 519 | 44.6% | 89.9% |
| IfcFlowTerminal | 84 | 7.2% | 97.1% |
| IfcFlowController | 28 | 2.4% | 99.5% |
| IfcBuildingElementProxy | 4 | 0.3% | 99.8% |
| IfcEnergyConversionDevice | 2 | 0.2% | 100.0% |


## Elements by size method

| size method | elements | share of elements | cumulative share |
| --- | --- | --- | --- |
| connected_segment_profile | 400 | 34.4% | 34.4% |
| circle_profile | 367 | 31.6% | 66.0% |
| connected_duct_segment | 168 | 14.4% | 80.4% |
| port_axis_against_extrusion | 116 | 10.0% | 90.4% |
| world_bbox | 74 | 6.4% | 96.7% |
| faceted_bbox_minor_axis | 20 | 1.7% | 98.5% |
| unresolved | 18 | 1.5% | 100.0% |


## Elements by family

| family | elements | share of elements | cumulative share |
| --- | --- | --- | --- |
| (none) | 399 | 34.3% | 34.3% |
| elbow | 229 | 19.7% | 54.0% |
| transition | 209 | 18.0% | 72.0% |
| rectangular | 116 | 10.0% | 81.9% |
| tee | 88 | 7.6% | 89.5% |
| round_flex | 36 | 3.1% | 92.6% |
| supply | 20 | 1.7% | 94.3% |
| return | 18 | 1.5% | 95.9% |
| panel | 16 | 1.4% | 97.2% |
| volume_damper | 14 | 1.2% | 98.5% |
| round | 10 | 0.9% | 99.3% |
| cross | 4 | 0.3% | 99.7% |
| cap | 2 | 0.2% | 99.8% |
| exhaust | 2 | 0.2% | 100.0% |


## Elements by cross-section shape

| shape | elements | share of elements | cumulative share |
| --- | --- | --- | --- |
| (none) | 644 | 55.4% | 55.4% |
| round | 403 | 34.7% | 90.0% |
| rectangular | 116 | 10.0% | 100.0% |


## Missing material, insulation and predefined type

Counts are size groups. The inventory found no material name and no insulation on these models.

| model | groups | groups with no material | groups with no insulation | groups with no predefined type | elements with no material |
| --- | --- | --- | --- | --- | --- |
| piping | 41 | 41 | 41 | 41 | 463 |
| ventilation | 40 | 40 | 40 | 40 | 374 |
| heating_and_cooling | 17 | 17 | 17 | 17 | 326 |

Size groups whose NominalDiameter property disagrees with the connected profile: 23 groups, 243 elements. Size groups with more than one outside diameter (reducers and similar): 17 groups, 132 elements.


## System assignments

The count is the sum of system memberships stored on each size group. It can exceed the element count.

| model | system object type | assignments | share of that model's assignments | elements in the model | assignments minus elements |
| --- | --- | --- | --- | --- | --- |
| piping | Domestic Cold Water | 199 | 41.0% | 463 | 22 |
| piping | Sanitary | 170 | 35.1% | 463 | 22 |
| piping | Domestic Hot Water | 116 | 23.9% | 463 | 22 |
| ventilation | Powietrze nawiewane | 188 | 49.3% | 374 | 7 |
| ventilation | Powietrze recyrkulacyjne | 186 | 48.8% | 374 | 7 |
| ventilation | Powietrze usuwane | 6 | 1.6% | 374 | 7 |
| ventilation | Kanalizacja | 1 | 0.3% | 374 | 7 |
| heating_and_cooling | Hydronic Return | 178 | 51.7% | 326 | 18 |
| heating_and_cooling | Hydronic Supply | 166 | 48.3% | 326 | 18 |


## Pipe segments by outside diameter

| model | OD mm | segments | share of segments | length m | share of pipe length | cumulative length share | mean length per segment m | match status | clamps | articles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heating_and_cooling | 9.52 | 81 | 22.7% | 130.103 | 42.8% | 42.8% | 1.606 | matched | 1 | 539443 |
| heating_and_cooling | 12.7 | 50 | 14.0% | 60.046 | 19.8% | 62.6% | 1.201 | matched | 1 | 079440 |
| piping | 22.225 | 76 | 21.3% | 43.338 | 14.3% | 76.8% | 0.57 | matched | 3 | 119862, 079442, 20845 |
| piping | 41.275 | 38 | 10.6% | 23.516 | 7.7% | 84.6% | 0.619 | matched | 3 | 119858, 079445, 20851 |
| piping | 15.875 | 54 | 15.1% | 18.446 | 6.1% | 90.7% | 0.342 | matched | 2 | 079441, 20843 |
| piping | 104.775 | 24 | 6.7% | 16.888 | 5.6% | 96.2% | 0.704 | matched | 3 | 064697, 3396105, 3403105 |
| piping | 12.7 | 6 | 1.7% | 6.121 | 2.0% | 98.2% | 1.02 | matched | 1 | 079440 |
| heating_and_cooling | 19.05 | 20 | 5.6% | 5.118 | 1.7% | 99.9% | 0.256 | matched | 1 | 119862 |
| piping | 15 | 8 | 2.2% | 0.256 | 0.1% | 100.0% | 0.032 | matched | 4 | 119866, 079440, 079441, 20843 |


## Pipe-segment diameter statistics

Min, max, mean, median and sample stdev treat one segment as one observation, so a common small diameter pulls the mean down. The length-weighted columns weight each size by its recorded centreline length.

| model | segments | length m | mean length per segment m | min OD mm | max OD mm | count-weighted mean OD mm | count-weighted median OD mm | count-weighted sample stdev mm | length-weighted mean OD mm | length-weighted median OD mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| piping | 206 | 108.565 | 0.527 | 12.7 | 104.775 | 33.134 | 22.225 | 27.582 | 37.56 | 22.225 |
| heating_and_cooling | 151 | 195.267 | 1.293 | 9.52 | 19.05 | 11.835 | 9.52 | 3.176 | 10.748 | 9.52 |
| all pipe segments | 357 | 303.832 | 0.851 | 9.52 | 104.775 | 24.125 | 15.875 | 23.524 | 20.328 | 12.7 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| distinct pipe-segment OD values, one row per size group, mm | 9 | 253.12 | 9.52 | 104.775 | 95.255 | 28.124 | 15.875 | 30.228 | 12.7 | 22.225 |


## Duct segments by cross-section

| model | shape | size | width mm | height mm | OD mm | section area mm2 | segments | length m | share of duct length | cumulative length share | mean length per segment m | match status | primary products |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ventilation | rectangular | 200.0 × 150.0 mm | 200 | 150 |  | 30000 | 46 | 43.655 | 36.9% | 36.9% | 0.949 | matched_with_assumption | 2 |
| ventilation | rectangular | 150.0 × 150.0 mm | 150 | 150 |  | 22500 | 30 | 31.835 | 26.9% | 63.8% | 1.061 | matched_with_assumption | 2 |
| ventilation | rectangular | 300.0 × 300.0 mm | 300 | 300 |  | 90000 | 22 | 21.939 | 18.5% | 82.3% | 0.997 | matched_with_assumption | 2 |
| ventilation | rectangular | 300.0 × 150.0 mm | 300 | 150 |  | 45000 | 18 | 11.051 | 9.3% | 91.6% | 0.614 | matched_with_assumption | 2 |
| ventilation | round | OD 150.0 mm |  |  | 150 |  | 10 | 9.896 | 8.4% | 100.0% | 0.99 | matched | 1 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rectangular duct width, one size group, mm | 4 | 950 | 150 | 300 | 150 | 237.5 | 250 | 75 | 187.5 | 300 |
| rectangular duct height, one size group, mm | 4 | 750 | 150 | 300 | 150 | 187.5 | 150 | 75 | 150 | 187.5 |
| rectangular section area, one size group, mm2 | 4 | 187500 | 22500 | 90000 | 67500 | 46875 | 37500 | 30233.467 | 28125 | 56250 |
| duct segment length, one size group, m | 5 | 118.376 | 9.896 | 43.655 | 33.759 | 23.675 | 21.939 | 14.301 | 11.051 | 31.835 |

Length-weighted mean rectangular width is 215.738 mm; height 180.336 mm; section area 41461.491 mm2.


## Devices and other bounding boxes

| model | kind | IFC class | size | elements | share of all elements | bbox axis 1 mm | bbox axis 2 mm | bbox axis 3 mm | status | gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| piping | sanitary_fixture | IfcFlowTerminal | bbox 228.2 × 510 × 635 mm | 4 | 0.3% | 228.2 | 510 | 635 | unmatched | No sanitary carrier or fixture bracket is in the database. |
| piping | sanitary_fixture | IfcFlowTerminal | bbox 361.9 × 584.3 × 722.5 mm | 4 | 0.3% | 361.9 | 584.3 | 722.5 | unmatched | No sanitary carrier or fixture bracket is in the database. |
| piping | sanitary_fixture | IfcFlowTerminal | bbox 457 × 457.2 × 485.8 mm | 4 | 0.3% | 457 | 457.2 | 485.8 | unmatched | No sanitary carrier or fixture bracket is in the database. |
| piping | water_heater | IfcBuildingElementProxy | bbox 350 × 500 × 1000 mm | 2 | 0.2% | 350 | 500 | 1000 | unmatched | No water-heater support is in the database. The proxy is a floor-standing appliance, not a suspended pipe. |
| ventilation | air_handling_unit | IfcBuildingElementProxy | bbox 475 × 1100 × 1400 mm | 2 | 0.2% | 475 | 1100 | 1400 | unmatched | No air-handling-unit frame is in the database. |
| ventilation | air_terminal | IfcFlowTerminal | bbox 101.6 × 200 × 200 mm | 18 | 1.5% | 101.6 | 200 | 200 | unmatched | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | IfcFlowTerminal | bbox 101.6 × 200 × 200 mm | 18 | 1.5% | 101.6 | 200 | 200 | unmatched | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | IfcFlowTerminal | bbox 40 × 300 × 300 mm | 2 | 0.2% | 40 | 300 | 300 | unmatched | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | IfcFlowTerminal | bbox 40 × 300 × 300 mm | 2 | 0.2% | 40 | 300 | 300 | unmatched | No diffuser or grille fixing is in the database. |
| heating_and_cooling | radiator | IfcFlowTerminal | bbox 100 × 350 × 1000 mm | 16 | 1.4% | 100 | 350 | 1000 | matched_with_assumption |  |
| heating_and_cooling | stove | IfcEnergyConversionDevice | bbox 350 × 500 × 1000 mm | 2 | 0.2% | 350 | 500 | 1000 | unmatched | No stove or boiler support is in the database. The element is floor-standing equipment. |


## Coverage by kind

| kind | groups | elements | matched elements | matched share | assumption elements | assumption share | unmatched elements | unmatched share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| air_handling_unit | 1 | 2 | 0 | 0.0% | 0 | 0.0% | 2 | 100.0% |
| air_terminal | 4 | 40 | 0 | 0.0% | 0 | 0.0% | 40 | 100.0% |
| duct_accessory | 3 | 14 | 0 | 0.0% | 14 | 100.0% | 0 | 0.0% |
| duct_fitting | 25 | 156 | 10 | 6.4% | 144 | 92.3% | 2 | 1.3% |
| duct_flex | 2 | 36 | 0 | 0.0% | 0 | 0.0% | 36 | 100.0% |
| duct_segment | 5 | 126 | 10 | 7.9% | 116 | 92.1% | 0 | 0.0% |
| pipe_accessory | 3 | 14 | 14 | 100.0% | 0 | 0.0% | 0 | 0.0% |
| pipe_fitting | 40 | 386 | 386 | 100.0% | 0 | 0.0% | 0 | 0.0% |
| pipe_segment | 9 | 357 | 357 | 100.0% | 0 | 0.0% | 0 | 0.0% |
| radiator | 1 | 16 | 0 | 0.0% | 16 | 100.0% | 0 | 0.0% |
| sanitary_fixture | 3 | 12 | 0 | 0.0% | 0 | 0.0% | 12 | 100.0% |
| stove | 1 | 2 | 0 | 0.0% | 0 | 0.0% | 2 | 100.0% |
| water_heater | 1 | 2 | 0 | 0.0% | 0 | 0.0% | 2 | 100.0% |


## Unmatched size groups

| model | kind | size | elements | share of that model | share of all elements | gap |
| --- | --- | --- | --- | --- | --- | --- |
| piping | sanitary_fixture | bbox 228.2 × 510 × 635 mm | 4 | 0.9% | 0.3% | No sanitary carrier or fixture bracket is in the database. |
| piping | sanitary_fixture | bbox 361.9 × 584.3 × 722.5 mm | 4 | 0.9% | 0.3% | No sanitary carrier or fixture bracket is in the database. |
| piping | sanitary_fixture | bbox 457 × 457.2 × 485.8 mm | 4 | 0.9% | 0.3% | No sanitary carrier or fixture bracket is in the database. |
| piping | water_heater | bbox 350 × 500 × 1000 mm | 2 | 0.4% | 0.2% | No water-heater support is in the database. The proxy is a floor-standing appliance, not a suspended pipe. |
| ventilation | air_handling_unit | bbox 475 × 1100 × 1400 mm | 2 | 0.5% | 0.2% | No air-handling-unit frame is in the database. |
| ventilation | air_terminal | bbox 101.6 × 200 × 200 mm | 18 | 4.8% | 1.5% | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | bbox 101.6 × 200 × 200 mm | 18 | 4.8% | 1.5% | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | bbox 40 × 300 × 300 mm | 2 | 0.5% | 0.2% | No diffuser or grille fixing is in the database. |
| ventilation | air_terminal | bbox 40 × 300 × 300 mm | 2 | 0.5% | 0.2% | No diffuser or grille fixing is in the database. |
| ventilation | duct_fitting | connected duct unresolved | 2 | 0.5% | 0.2% | No connected duct size was recovered, so no duct hanger can be selected. |
| ventilation | duct_flex | mesh minor axis 151.6 mm | 20 | 5.3% | 1.7% | No product has a clamping range covering flex-duct mesh minor axis 151.6 mm. Sikla PLU type 150 is a spiral-seam clamp for nominal 150 mm and is not applied. |
| ventilation | duct_flex | diameter unresolved | 16 | 4.3% | 1.4% | Flex-duct diameter could not be recovered from the mesh, and no flex-duct hanger is in the database. |
| heating_and_cooling | stove | bbox 350 × 500 × 1000 mm | 2 | 0.6% | 0.2% | No stove or boiler support is in the database. The element is floor-standing equipment. |

Unmatched groups: 13. Unmatched elements: 96 (8.3% of 1163).


## Primary-product utilisation

Element hits sum the size groups for which the product is a primary match. A reducer that matches two clamps, and a diameter that matches three clamps, are counted once for each product. The shares can therefore sum to more than 100%.

| id | manufacturer | article | element type | groups | element hits | share of all elements |
| --- | --- | --- | --- | --- | --- | --- |
| sikla-luw-sl-189893 | Sikla | 189893 | duct_rectangular | 29 | 274 | 23.6% |
| sikla-luw-sz-189902 | Sikla | 189902 | duct_rectangular | 29 | 274 | 23.6% |
| muepro-optimal-119862 | Müpro | 119862 | pipe | 18 | 252 | 21.7% |
| fischer-frs-plus-079442 | fischer | 079442 | pipe | 12 | 200 | 17.2% |
| hilti-mp-mi-20845 | Hilti | 20845 | pipe | 12 | 200 | 17.2% |
| fischer-frs-l-539443 | fischer | 539443 | pipe | 7 | 184 | 15.8% |
| fischer-frs-plus-079440 | fischer | 079440 | pipe | 16 | 174 | 15.0% |
| fischer-frs-plus-079441 | fischer | 079441 | pipe | 12 | 147 | 12.6% |
| hilti-mp-mi-20843 | Hilti | 20843 | pipe | 12 | 147 | 12.6% |
| fischer-frs-plus-079445 | fischer | 079445 | pipe | 10 | 84 | 7.2% |
| hilti-mp-mi-20851 | Hilti | 20851 | pipe | 10 | 84 | 7.2% |
| muepro-optimal-119858 | Müpro | 119858 | pipe | 10 | 84 | 7.2% |
| fischer-frs-a2-064697 | fischer | 064697 | pipe | 8 | 60 | 5.2% |
| walraven-bismat-2000-3403105 | Walraven | 3403105 | pipe | 8 | 60 | 5.2% |
| walraven-bismat-ksb2-3396105 | Walraven | 3396105 | pipe | 8 | 60 | 5.2% |
| sikla-plu-2g-199893 | Sikla | 199893 | duct_round | 7 | 34 | 2.9% |
| muepro-optimal-119866 | Müpro | 119866 | pipe | 3 | 20 | 1.7% |
| kermi-console-zb02870003 | Kermi | ZB02870003 | radiator | 1 | 16 | 1.4% |

Primary products with no hit in this inventory: none. Primary products with at least one hit: 18 of 18.

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| element hits per primary product | 18 | 2354 | 16 | 274 | 258 | 130.778 | 115.5 | 86.41 | 60 | 196 |


## Companion products under two substrates

Companions are rods, channel and anchors returned with a primary match. substrate none is the duplex default. substrate concrete is the German commercial ceiling the anchor articles were recorded for. Each element is counted once per companion: a rod is attached when the matched clamps use that thread, and it is not multiplied by the number of clamps.

| id | element type | threads | groups, substrate none | elements, substrate none | groups, substrate concrete | elements, substrate concrete |
| --- | --- | --- | --- | --- | --- | --- |
| hilti-mq-41-3-369596 | channel | M12 | 29 | 274 | 29 | 274 |
| hilti-rod-am8-339793 | threaded_rod | M8 | 84 | 1051 | 84 | 1051 |
| hilti-rod-am10-339795 | threaded_rod | M10 | 84 | 1051 | 84 | 1051 |
| fischer-ea-ii-m8-532231 | ceiling_anchor | M8 | 0 | 0 | 84 | 1051 |
| fischer-ea-ii-m10-532232 | ceiling_anchor | M10 | 0 | 0 | 84 | 1051 |


## Size-group census

| model | kind | family | IFC class | size | elements | length m | size method | shape | status | primary products | assumption notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| piping | pipe_accessory | (none) | IfcFlowController | OD 22.225 mm | 8 |  | connected_segment_profile | (none) | matched | 3 | 0 |
| piping | pipe_accessory | (none) | IfcFlowController | OD 15.875 mm | 2 |  | connected_segment_profile | (none) | matched | 2 | 0 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 22.225 mm | 38 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 15.875 mm | 34 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 22.225 mm | 22 |  | connected_segment_profile | (none) | matched | 3 | 0 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 41.275 mm | 20 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 15.875 / 22.225 mm | 18 |  | connected_segment_profile | (none) | matched | 5 | 0 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 104.775 mm | 12 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 15.875 / 22.225 mm | 10 |  | connected_segment_profile | (none) | matched | 5 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 22.225 / 104.775 mm | 10 |  | connected_segment_profile | (none) | matched | 6 | 0 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 22.225 mm | 10 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 15 / 15.875 mm | 8 |  | connected_segment_profile | (none) | matched | 4 | 0 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 41.275 mm | 6 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 15.875 mm | 5 |  | connected_segment_profile | (none) | matched | 2 | 0 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 12.7 mm | 4 |  | connected_segment_profile | (none) | matched | 1 | 0 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 15 / 41.275 mm | 4 |  | connected_segment_profile | (none) | matched | 7 | 0 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 41.275 / 104.775 mm | 4 |  | connected_segment_profile | (none) | matched | 6 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 41.275 / 104.775 mm | 4 |  | connected_segment_profile | (none) | matched | 6 | 0 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 104.775 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 104.775 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 12.7 / 41.275 mm | 2 |  | connected_segment_profile | (none) | matched | 4 | 0 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 12.7 / 41.275 mm | 2 |  | connected_segment_profile | (none) | matched | 4 | 0 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 12.7 mm | 2 |  | connected_segment_profile | (none) | matched | 1 | 1 |
| piping | pipe_fitting | elbow | IfcFlowFitting | OD 15.875 / 22.225 mm | 2 |  | connected_segment_profile | (none) | matched | 5 | 1 |
| piping | pipe_fitting | tee | IfcFlowFitting | OD 22.225 / 104.775 mm | 2 |  | connected_segment_profile | (none) | matched | 6 | 1 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 22.225 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 22.225 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 1 |
| piping | pipe_fitting | transition | IfcFlowFitting | OD 41.275 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 0 |
| piping | pipe_fitting | cap | IfcFlowTerminal | OD 41.275 mm | 2 |  | connected_segment_profile | (none) | matched | 3 | 0 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 15.875 mm | 1 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| piping | pipe_fitting | (none) | IfcFlowFitting | OD 15.875 mm | 1 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 22.225 mm | 76 | 43.338 | circle_profile | round | matched | 3 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 15.875 mm | 54 | 18.446 | circle_profile | round | matched | 2 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 41.275 mm | 38 | 23.516 | circle_profile | round | matched | 3 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 104.775 mm | 24 | 16.888 | circle_profile | round | matched | 3 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 15.0 mm | 8 | 0.256 | circle_profile | round | matched | 4 | 1 |
| piping | pipe_segment | (none) | IfcFlowSegment | OD 12.7 mm | 6 | 6.121 | circle_profile | round | matched | 1 | 1 |
| piping | sanitary_fixture | (none) | IfcFlowTerminal | bbox 228.2 × 510 × 635 mm | 4 |  | world_bbox | (none) | unmatched | 0 | 0 |
| piping | sanitary_fixture | (none) | IfcFlowTerminal | bbox 361.9 × 584.3 × 722.5 mm | 4 |  | world_bbox | (none) | unmatched | 0 | 0 |
| piping | sanitary_fixture | (none) | IfcFlowTerminal | bbox 457 × 457.2 × 485.8 mm | 4 |  | world_bbox | (none) | unmatched | 0 | 0 |
| piping | water_heater | (none) | IfcBuildingElementProxy | bbox 350 × 500 × 1000 mm | 2 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | air_handling_unit | (none) | IfcBuildingElementProxy | bbox 475 × 1100 × 1400 mm | 2 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | air_terminal | supply | IfcFlowTerminal | bbox 101.6 × 200 × 200 mm | 18 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | air_terminal | return | IfcFlowTerminal | bbox 101.6 × 200 × 200 mm | 18 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | air_terminal | exhaust | IfcFlowTerminal | bbox 40 × 300 × 300 mm | 2 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | air_terminal | supply | IfcFlowTerminal | bbox 40 × 300 × 300 mm | 2 |  | world_bbox | (none) | unmatched | 0 | 0 |
| ventilation | duct_accessory | volume_damper | IfcFlowController | connected 200×150 mm | 6 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_accessory | volume_damper | IfcFlowController | connected 150×150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_accessory | volume_damper | IfcFlowController | connected 300×150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 200×150 mm | 28 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 150×150 mm | 26 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | elbow | IfcFlowFitting | connected 200×150 mm | 12 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | elbow | IfcFlowFitting | connected 150×150 mm | 10 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | elbow | IfcFlowFitting | connected 300×300 mm | 10 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 200×150 mm | 8 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected Ø150 mm | 8 |  | connected_duct_segment | (none) | matched | 1 | 0 |
| ventilation | duct_fitting | elbow | IfcFlowFitting | connected 300×150 mm | 6 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected Ø150, 200×150 mm | 6 |  | connected_duct_segment | (none) | matched_with_assumption | 3 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 150×150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 150×150, 300×300, 200×150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 200×150, 300×300, 150×150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 200×150, Ø150 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 3 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 300×150, 300×300 mm | 4 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 150×150, 200×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 150×150, 300×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 150×150, 300×150, 200×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 200×150, 150×150, 300×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected 300×150, 200×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | tee | IfcFlowFitting | connected 300×150, Ø150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 3 | 0 |
| ventilation | duct_fitting | cross | IfcFlowFitting | connected 300×300, 150×150, 200×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | cross | IfcFlowFitting | connected 300×300, 200×150, 150×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 2 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected duct unresolved | 2 |  | unresolved | (none) | unmatched | 0 | 0 |
| ventilation | duct_fitting | elbow | IfcFlowFitting | connected Ø150 mm | 2 |  | connected_duct_segment | (none) | matched | 1 | 0 |
| ventilation | duct_fitting | transition | IfcFlowFitting | connected Ø150, 300×150 mm | 2 |  | connected_duct_segment | (none) | matched_with_assumption | 3 | 0 |
| ventilation | duct_flex | round_flex | IfcFlowSegment | mesh minor axis 151.6 mm | 20 |  | faceted_bbox_minor_axis | round | unmatched | 0 | 1 |
| ventilation | duct_flex | round_flex | IfcFlowSegment | diameter unresolved | 16 |  | unresolved | round | unmatched | 0 | 1 |
| ventilation | duct_segment | rectangular | IfcFlowSegment | 200.0 × 150.0 mm | 46 | 43.655 | port_axis_against_extrusion | rectangular | matched_with_assumption | 2 | 0 |
| ventilation | duct_segment | rectangular | IfcFlowSegment | 150.0 × 150.0 mm | 30 | 31.835 | port_axis_against_extrusion | rectangular | matched_with_assumption | 2 | 0 |
| ventilation | duct_segment | rectangular | IfcFlowSegment | 300.0 × 300.0 mm | 22 | 21.939 | port_axis_against_extrusion | rectangular | matched_with_assumption | 2 | 0 |
| ventilation | duct_segment | rectangular | IfcFlowSegment | 300.0 × 150.0 mm | 18 | 11.051 | port_axis_against_extrusion | rectangular | matched_with_assumption | 2 | 0 |
| ventilation | duct_segment | round | IfcFlowSegment | OD 150.0 mm | 10 | 9.896 | circle_profile | round | matched | 1 | 0 |
| heating_and_cooling | pipe_accessory | (none) | IfcFlowController | OD 19.05 mm | 4 |  | connected_segment_profile | (none) | matched | 1 | 0 |
| heating_and_cooling | pipe_fitting | elbow | IfcFlowFitting | OD 9.52 mm | 37 |  | connected_segment_profile | (none) | matched | 1 | 1 |
| heating_and_cooling | pipe_fitting | transition | IfcFlowFitting | OD 9.52 / 12.7 mm | 30 |  | connected_segment_profile | (none) | matched | 2 | 0 |
| heating_and_cooling | pipe_fitting | elbow | IfcFlowFitting | OD 12.7 mm | 22 |  | connected_segment_profile | (none) | matched | 1 | 1 |
| heating_and_cooling | pipe_fitting | tee | IfcFlowFitting | OD 9.52 / 12.7 mm | 20 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| heating_and_cooling | pipe_fitting | elbow | IfcFlowTerminal | OD 9.52 mm | 12 |  | connected_segment_profile | (none) | matched | 1 | 0 |
| heating_and_cooling | pipe_fitting | transition | IfcFlowFitting | OD 12.7 / 19.05 mm | 8 |  | connected_segment_profile | (none) | matched | 2 | 0 |
| heating_and_cooling | pipe_fitting | transition | IfcFlowFitting | OD 19.05 mm | 8 |  | connected_segment_profile | (none) | matched | 1 | 0 |
| heating_and_cooling | pipe_fitting | elbow | IfcFlowFitting | OD 19.05 mm | 8 |  | connected_segment_profile | (none) | matched | 1 | 1 |
| heating_and_cooling | pipe_fitting | tee | IfcFlowFitting | OD 12.7 / 19.05 mm | 4 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| heating_and_cooling | pipe_fitting | tee | IfcFlowFitting | OD 9.52 / 12.7 mm | 2 |  | connected_segment_profile | (none) | matched | 2 | 1 |
| heating_and_cooling | pipe_fitting | tee | IfcFlowTerminal | OD 9.52 / 12.7 mm | 2 |  | connected_segment_profile | (none) | matched | 2 | 0 |
| heating_and_cooling | pipe_segment | (none) | IfcFlowSegment | OD 9.52 mm | 81 | 130.103 | circle_profile | round | matched | 1 | 1 |
| heating_and_cooling | pipe_segment | (none) | IfcFlowSegment | OD 12.7 mm | 50 | 60.046 | circle_profile | round | matched | 1 | 1 |
| heating_and_cooling | pipe_segment | (none) | IfcFlowSegment | OD 19.05 mm | 20 | 5.118 | circle_profile | round | matched | 1 | 1 |
| heating_and_cooling | radiator | panel | IfcFlowTerminal | bbox 100 × 350 × 1000 mm | 16 |  | world_bbox | (none) | matched_with_assumption | 1 | 0 |
| heating_and_cooling | stove | (none) | IfcEnergyConversionDevice | bbox 350 × 500 × 1000 mm | 2 |  | world_bbox | (none) | unmatched | 0 | 0 |


## Architecture storeys

| name | elevation m |
| --- | --- |
| T/FDN | -1.25 |
| Level 1 | 0 |
| Level 2 | 3.1 |
| Roof | 6 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| storey elevation, m | 4 | 7.85 | -1.25 | 6 | 7.25 | 1.962 | 1.55 | 3.254 | -0.312 | 3.825 |


## Architecture slabs and roofs

| type | predefined type | thickness mm | z min m | z max m | count |
| --- | --- | --- | --- | --- | --- |
| Floor:127mm Slab on Grade | FLOOR | 127 | -0.127 | 0 | 2 |
| Floor:Residential - Wood Joist with Subflooring | FLOOR | 305 | 2.795 | 3.1 | 2 |
| Floor:Finish Floor - Wood | FLOOR | 19 | 3.1 | 3.119 | 6 |
| Floor:Finish Floor - Ceramic Tile | FLOOR | 13 | 3.1 | 3.113 | 2 |
| Floor:Finish Floor - Wood | FLOOR | 19 | 0 | 0.019 | 2 |
| Floor:Finish Floor - Ceramic Tile | FLOOR | 13 | 0 | 0.013 | 4 |
| Basic Roof:Live Roof over Wood Joist Flat Roof | ROOF | 457 | 6 | 6.457 | 1 |
| Floor:150mm Exterior Slab on Grade | FLOOR | 150 | -0.137 | 0.013 | 2 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| slabs thickness, one type row, mm | 8 | 1103 | 13 | 457 | 444 | 137.875 | 73 | 164.528 | 17.5 | 188.75 |
| slabs thickness, one instance, mm | 21 | 1851 | 13 | 457 | 444 | 88.143 | 19 | 125.081 | 13 | 127 |


## Architecture ceilings

| type | predefined type | thickness mm | z min m | z max m | count |
| --- | --- | --- | --- | --- | --- |
| Compound Ceiling:Gypsum Board | CEILING | 57 | 2.5 | 2.557 | 4 |
| Compound Ceiling:Gypsum Board | CEILING | 57 | 5.6 | 5.657 | 8 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ceilings thickness, one type row, mm | 2 | 114 | 57 | 57 | 0 | 57 | 57 | 0 |  |  |
| ceilings thickness, one instance, mm | 12 | 684 | 57 | 57 | 0 | 57 | 57 | 0 | 57 | 57 |


## Architecture beams

| type | predefined type | thickness mm | z min m | z max m | count |
| --- | --- | --- | --- | --- | --- |
| M_W-Wide Flange:W310X60 | (none) | 303 | 2.797 | 3.1 | 2 |
| M_W-Wide Flange:W410X60 | (none) | 407 | 2.693 | 3.1 | 2 |
| M_W-Wide Flange:W410X60 | (none) | 407 | 5.593 | 6 | 4 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| beams thickness, one type row, mm | 3 | 1117 | 303 | 407 | 104 | 372.333 | 407 | 60.044 |  |  |
| beams thickness, one instance, mm | 8 | 3048 | 303 | 407 | 104 | 381 | 407 | 48.143 | 381 | 407 |


## Ceiling to structure gaps

| ceiling z max m | ceiling thickness mm | overhead | overhead z min m | gap mm | ceilings |
| --- | --- | --- | --- | --- | --- |
| 2.557 | 57 | Floor:Residential - Wood Joist with Subflooring | 2.795 | 238 | 4 |
| 5.657 | 57 | Basic Roof:Live Roof over Wood Joist Flat Roof | 6 | 343 | 8 |

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clear gap, one ceiling instance, mm | 12 | 3696 | 238 | 343 | 105 | 308 | 343 | 51.698 | 238 | 343 |
| ceiling thickness in the gap table, one instance, mm | 12 | 684 | 57 | 57 | 0 | 57 | 57 | 0 | 57 | 57 |

The floor and roof build-ups above the rooms use dimensional lumber and plywood, not a concrete soffit.

Ceilings are compound gypsum board on a metal-stud layer (57 mm in the material layer set), so a concrete ceiling anchor does not match this model's soffit.

Concrete in this architecture model is the slab on grade and the foundation walls, not the ceiling the MEP hangers would reach.


## Sources

| series | n | sum | min | max | range | mean | median | sample stdev | q1 | q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sources cited by one product | 23 | 31 | 1 | 2 | 1 | 1.348 | 1 | 0.487 | 1 | 2 |

| accessed | citations | share of citations | cumulative share |
| --- | --- | --- | --- |
| 2026-10-18 | 36 | 100.0% | 100.0% |

| source host | citations | share of citations | cumulative share |
| --- | --- | --- | --- |
| www.meinhausshop.de | 5 | 13.9% | 13.9% |
| www.dibt.de | 4 | 11.1% | 25.0% |
| www.muepro.de | 3 | 8.3% | 33.3% |
| 1001krep.ru | 3 | 8.3% | 41.7% |
| www.sikla.de | 3 | 8.3% | 50.0% |
| heizung-billiger.de | 2 | 5.6% | 55.6% |
| assets.hilti.com | 2 | 5.6% | 61.1% |
| www.fischer.de | 2 | 5.6% | 66.7% |
| fiproductmedia.azureedge.net | 2 | 5.6% | 72.2% |
| www.fischer-international.com | 1 | 2.8% | 75.0% |
| www.unielektro.de | 1 | 2.8% | 77.8% |
| shop.famo24.de | 1 | 2.8% | 80.6% |
| www.sikla.ch | 1 | 2.8% | 83.3% |
| www.hilti.de | 1 | 2.8% | 86.1% |
| www.beijerref.de | 1 | 2.8% | 88.9% |
| storage.ua.prom.st | 1 | 2.8% | 91.7% |
| itsolution.lindab.com | 1 | 2.8% | 94.4% |
| cdn.standards.iteh.ai | 1 | 2.8% | 97.2% |
| doi.org | 1 | 2.8% | 100.0% |

| title | url | citations | host |
| --- | --- | --- | --- |
| fischer datasheet Rohrschelle FRS Plus | https://www.meinhausshop.de/media/pdf/94_046_22--DBL-01-de.pdf | 4 | www.meinhausshop.de |
| Distributor reproduction of the Hilti MP-MI load table | https://1001krep.ru/f/mp-mi.pdf | 3 | 1001krep.ru |
| ETA-18/0130 Hilti MP-MI pipe clamps | https://www.dibt.de/pdf_storage/2024/ETA-18!0130(8.06.02-122!21).pdf | 3 | www.dibt.de |
| Müpro OPTIMAL Rohrschelle article table | https://www.muepro.de/Produkte/Befestigungstechnik/Rohrschellen/OPTIMAL.html | 3 | www.muepro.de |
| fischer EA II permissible-load table | https://fiproductmedia.azureedge.net/media/Marketing%20Materials/Sales%20Materials/VKU_EAII_F_SDE_AIP_V2.pdf | 2 | fiproductmedia.azureedge.net |
| fischer SHK catalogue, Einschlaganker EA II article table | https://www.fischer.de/-/media/fixing-systems/rebrush/fide/service/infos-und-updates/informationsmaterial/documents/kataloge/katalog-sanitaer-v1.pdf | 2 | www.fischer.de |
| Sikla Lüftungswinkel LUW | https://www.sikla.de/startseite-131533/produkte-131535/e-katalog-131895/siconnect-3832/lueftung-10505/lueftungswinkel-luw-4160 | 2 | www.sikla.de |
| Hilti manual, medium-light installation systems, M8 threaded rod table | https://assets.hilti.com/api/public/content/5021068-original?v=Manuale+Sistemi+installazione+medio+leggere.pdf | 1 | assets.hilti.com |
| Hilti manual, medium-light installation systems, M10 threaded rod table | https://assets.hilti.com/api/public/content/5021068-original?v=Manuale+Sistemi+installazione+medio+leggere.pdf | 1 | assets.hilti.com |
| EN 12236:2002 preview (SIST EN 12236:2002) | https://cdn.standards.iteh.ai/samples/6392/f9a3d57c81574acb8ee255867c6daaca/SIST-EN-12236-2002.pdf | 1 | cdn.standards.iteh.ai |
| DIN EN 12236:2002-04 bibliographic record | https://doi.org/10.31030/9199301 | 1 | doi.org |
| Kermi Wandkonsolen-Set ZB02870003 reseller technical text | https://heizung-billiger.de/44039-kermi-wandkonsolen-set-variabel-mit-tiefenverstellung-wa-60-100-mm-weiss-kermi-zb02870003-4037486266503.html | 1 | heizung-billiger.de |
| Walraven BISMAT 2000 100–105 mm reseller listing (3403105) | https://heizung-billiger.de/727280-walraven-bismat-rohrschelle-2000-100-105mm-m8-m10-zweischraubenschelle-epdm-stahl-elektrolytisch-verzinkt-walraven-3403105-8712993004126.html | 1 | heizung-billiger.de |
| Lindab Ventilation, Upphängning av ventilationssystem | https://itsolution.lindab.com/lindabwebproductsdoc/pdf/documentation/ads/se/mounting/upphangning-ventsystem.pdf | 1 | itsolution.lindab.com |
| Walraven BIS KSB 2 100–105 mm reseller listing (Werksnummer 3396105) | https://shop.famo24.de/bis-zweischraubenschelle-ksb-2-100-105-mm-m8-10-ev-epdm/14810134 | 1 | shop.famo24.de |
| IBP technical catalogue, section 4.5 Befestigungsabstände | https://storage.ua.prom.st/657649_supersan_ibp_tk_all.pdf | 1 | storage.ua.prom.st |
| Conex installation notes, section 3.4 Befestigungsabstände | https://www.beijerref.de/media/ed/5c/fb/1758265815/conex-allgemeine-installationshinweise-ast-2241085.pdf | 1 | www.beijerref.de |
| ETA-18/0119 Hilti MQ installation channels | https://www.dibt.de/pdf_storage/2024/ETA-18!0119(8.06.02-121!21).pdf | 1 | www.dibt.de |
| fischer Pipe clamp FRS-L Universal | https://www.fischer-international.com/en/products/installation-systems/pipe-clamps/two-screw-pipe-clamps/pipe-clamp-frs-l-universal | 1 | www.fischer-international.com |
| Hilti MQ-41/3 product page | https://www.hilti.de/c/CLS_MODULAR_SUPPORT_SYSTEM/CLS_MODULAR_SUPPORT_PRO/r6130 | 1 | www.hilti.de |
| fischer datasheet Rohrschellen FRS A2/A4 | https://www.meinhausshop.de/media/pdf/meinhausshop-frs-a2-de.pdf | 1 | www.meinhausshop.de |
| Sikla Lüftungsschelle PLU 2G-N m.E. | https://www.sikla.ch/startseite-131533/produkte-131535/e-katalog-131895/siconnect-3832/lueftung-10505/lueftungsschelle-plu-2g-n-me-116704 | 1 | www.sikla.ch |
| Sikla Montagetechnik, Lüftungswinkel SZ note | https://www.sikla.de/fast/600/Montagetechnik_2023-04.pdf | 1 | www.sikla.de |
| Reseller listing FISCHER 539443 FRS-L Universal 8-11 | https://www.unielektro.de/FISCHER-539443-FRS-L-Universal-8-11-Rohrschelle--item-01253925 | 1 | www.unielektro.de |

Distinct source URLs: 24. Citations counting a reused URL once per product or guidance record: 36.


## Assumptions stored on products

| id | assumption |
| --- | --- |
| sikla-luw-sl-189893 | The LUW datasheet describes suspension of rectangular ducts and does not publish a width or height window. |
| sikla-luw-sz-189902 | The LUW datasheet describes the SZ angle for a wide, low rectangular duct and does not publish a width or height window. |
| kermi-console-zb02870003 | The console is for Kermi radiators with hanging lugs 25 mm high and 2 mm thick. The duplex IFC radiator is named only Radiator and does not state a manufacturer or lugs. |

Product assumption strings: 3 on 3 products.

IFC2X3 export: pipes and ducts are IfcFlowSegment, not IfcPipeSegment / IfcDuctSegment.

Segment property sets have length and roughness, not nominal diameter. Outside diameter is the circle-profile diameter.

Rectangular duct profiles mix run length into the profile. Width and height are the two edges that are not the port-to-port direction; height is the edge closer to world Z.

No insulation covering or insulation property was found on the MEP elements.

On fittings, NominalDiameter is an IfcPropertyListValue and often disagrees with the connected pipe's circle-profile diameter. Groups keep both; the profile diameter is the one a clamp has to fit.

Material entities on the MEP models are unnamed.
