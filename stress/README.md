# README GIF stress tests

These fixtures repeat the existing recording to measure real GIF bytes, turns and duration. The long-hold fixture extends only the static reverse-face reading interval. They are benchmarks, not the revised profile design.

- [3-cycles](3-cycles/README.md): 20,386,044 bytes, 72.0 seconds, 6 turns.
- [7-cycles](7-cycles/README.md): 47,567,136 bytes, 168.0 seconds, 14 turns.
- [15-cycles](15-cycles/README.md): 101,929,320 bytes, 360.0 seconds, 30 turns.
- [long-hold](long-hold/README.md): 6,794,462 bytes, 669.73 seconds, 2 turns.

## Native Markdown recording

- [Largest whole-cycle native fixture](native-max/README.md): 99,729,486 bytes, 216 seconds and 18 turns. Nine complete copies fit; ten exceed the ordinary Git limit.
- [One-hour duration fixture](native-hour/README.md): 11,091,989 bytes, 3,600 seconds and two turns. Only the static reverse-face hold is extended.

The earlier compact fixture and the new native fixture have different byte costs per turn. There is no universal maximum turn count or overall GIF duration. The frame delay field is 16 bits, so the hour fixture splits its hold across several frames.

## Verified behavior

The earlier 101,929,320-byte fixture loads and animates inside GitHub's rendered README, continues through its six-minute timeline and animates after the loop restarts. The other compact fixtures also load and animate. These checks establish that 10 MB is not a general repository-hosted README image limit. The native 99,729,486-byte fixture also loads and animates through its full 216-second timeline, with motion confirmed after the loop restarts. The one-hour fixture loads and animates at the beginning of its timeline. Browser measurements are in [verification.json](verification.json).

Adding a tenth complete native cycle produces 110,810,515 bytes, 240 seconds and 20 turns. That locally built file exceeds the documented limit and was not uploaded. These turn counts repeat the same two faces; different content changes the byte cost.

The one-hour fixture passes an independent Gifsicle duration sum of 3,600 seconds. Pillow also verifies that all six extended hold frames match the original static reverse face. A full hour of real-time browser playback has not been observed.

Load times were measured in isolated Chromium with browser cache disabled and no network throttling. CDN cache and connection conditions were not controlled, so these timings are observations rather than guarantees.

GitHub documents a 100 MiB (104,857,600-byte) ordinary Git file limit and a warning above 50 MiB. Attachments have a separate 10 MB image/GIF limit. This experiment uses committed repository files, without Git LFS or external hosting.

Sources: [GitHub large-file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), [attachment limits](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files), [GIF89a specification](https://giflib.sourceforge.net/gifstandard/GIF89a.html).
