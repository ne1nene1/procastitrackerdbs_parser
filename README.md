# procastitrackerdbs_parser
a parser for [procastitracker](https://strlen.com/procrastitracker/) database

## usage:

```python
import procastitrackerdbs_parser as proparser

# parse database
my_db = proparser.load_db("path/to/procastitracker/database/db.PT")

# flatten database structure
my_data_flatten = my_db.flatten_node_tree()
```

## explanation:
please read procastitracker database's file format spec by the author [here](https://github.com/aardappel/procrastitracker/blob/master/PT/file_format.txt) to get a better understanding of how this script works

### procastitrackerdbs_parser.load_db(file_path)
parse procastitracker database file in path file_path
return procastitrackerdbs_parser.Database object

### procastitrackerdbs_parser.Database.flatten_node_tree()
the flatten_node_tree method will flatten all Node object and all Day object associated with them, and return a list of lists in this structure:
```python
[
    [date, times, name, tag, day.activeseconds, day.semiidleseconds, day.key, day.lmb, day.rmb, day.scrollwheell]
    [  .     .     .     .           .                   .              .        .        .        .            ]
    [  .     .     .     .           .                   .              .        .        .        .            ]
    [  .     .     .     .           .                   .              .        .        .        .            ]
    [  .     .     .     .           .                   .              .        .        .        .            ]
    [  .     .     .     .           .                   .              .        .        .        .            ]
]
```
 - date: isodate of entry in %Y-%m-%d format (ex. 2025-05-05)
 - times: time of the day in %H:%M:%S format (ex. 16:54:32)
 - name: name of the entry (delete all null bytes)
 - tag: tag of the entry (get tag from tagindex)
 - day.activeseconds: active second of the entry in 
 - day.semiidleseconds

... the rest are self-explanatory

(note: day.activeseconds and day.semiidleseconds are in %H:%M:%S format while day.key, day.lmb, day.rmb, day.scrollwheell are in int)

notice that this method will automatically clean up the name of node as well as getting tag of the node too.

## author
@ne1nene (Soulmine) [github](https://github.com/ne1nene1/)
