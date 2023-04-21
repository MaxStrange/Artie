# Byte Stuffing in CAN

Whenever a CAN protocol in Artie specifies byte stuffing, it refers to this specification.

A simple byte stuffing procedure is used, and it works like this:

1. The first byte of payload is a special byte. This byte can either be 0xFF, which means
   there is no data, or it can be a number 0x00 to 0xFE, indicating the index (starting at
   the next byte as zero) of the next special byte.
1. All bytes starting after this first byte up until the next special byte are payload data.
1. Repeat.

As such, a special byte must be inserted every 254 bytes at farthest.

Also notice that this scheme will never make use of a 0x00 special byte. If a decoder
sees one, it means something has gone wrong.

Here are some examples:

**No data**:

```
[0xFF]
```

**One Byte of Payload Data**:

```
[0x01][data byte][0xFF]
```

**Two Bytes of Payload Data**:

```
[0x02][data byte][data byte][0xFF]
```

**255 Bytes of Payload Data**:

```
                                                              Final data byte
                                                              (the 255th byte total)
                                                                v
[0xFE][index 0 byte][index 1 byte][...][index 253 byte][0x01][index 0 byte][0xFF]
 ^                                      ^               ^                   ^
Points to the next                     Data byte       Special byte         Final special byte
special byte, found                    index 253      found at index 254
at index 254, starting                 (254th byte    says next special
from the byte right                    total)         byte is found at
after this one (as index 0)                           index 1 starting
                                                      from the byte right
                                                      after this one
                                                      as index 0
```

**254 Bytes of Payload Data**:

```
[0xFE][index 0 byte][index 1 byte][...][index 253 byte][0xFF]
 ^                                      ^               ^
Points to the next                     Data byte       Final special byte
special byte, found                    index 253
at index 254, starting                 (254th byte
from the byte right                    total)
after this one (as index 0)
```
