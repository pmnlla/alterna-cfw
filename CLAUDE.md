# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Policy

**This project does not accept AI-assisted code contributions.** Per `AGENTS.md`, all patches must be written and understood by the contributor personally. Do not generate, modify, or suggest code changes for this repository. Do not create PRs to any associated repos.

## Project Overview

Alterna is a custom firmware project for the Lorex LHA2104 DVR. The workflow centers on extracting the stock firmware blob, applying `quilt` patches to the extracted rootfs, and repackaging.

## Workflow Commands

All tasks are run via `mise`:

```sh
mise run fetch-toolchain  # Fetch the cross toolchain into .toolchain/
mise run extract          # Extract firmware.bin → build/rootfs/ (unsquashfs Squashfs_rootfs_1)
mise run set_patchset     # Set the active patchset (QUILT_PATCHSET env var)
mise run load             # Apply all patches (quilt push -a)
mise run new <name>       # Create a new patch file in the active patchset
mise run seal             # Refresh and pop all patches (quilt pop -a); reverts rootfs to stock
mise run build            # Full build: pack.sh rsup → fstable.py → crc.py; writes build/update.bin
mise run clean            # Remove build artifacts
```

Quilt patch management requires `QUILT_PATCHSET` to be set before running `new`, `load`, or `seal`. The patchset name corresponds to a subdirectory under `sys/patches/`.

`mise run build` needs `.toolchain/` populated (`mise run fetch-toolchain`) — `mise.toml` exports `TC`, `CC`, and `SYSROOT` from it, and any `acquire` recipe that cross-compiles will fail without it.

## Architecture

**Firmware layout** (`tooling/parts.py`): The stock `firmware.bin` is a flat binary containing two CRC tables, a uImage header, a Linux 3.10 ARM kernel (zImage + LZMA), and three Squashfs 4.0 (xz-compressed) root filesystems. Extraction targets `Squashfs_rootfs_1` (offset `0x293C1C`) as the primary rootfs.

`parts.py` offsets describe the **update-image (RSUp) layout**, not the device's flash layout. The on-flash layout comes from the U-Boot environment / kernel cmdline `mtdparts`; on the 2104 it is `448K(boot),3M(kernel),6656K(rootfs),16768K(app),5376K(www),384K(para),64K(p2p)` with `root=/dev/mtdblock2`. Don't use one to reason about the other.

**Inclusions** (`sys/inclusions.yaml`): Files grafted into the rootfs before packing, consumed by `include()` in `tooling/pack.sh`. Per-entry keys:

| key | meaning |
|---|---|
| `src` | path relative to repo root |
| `dest` | path inside the rootfs |
| `needs` | `selfAcquire` if the artifact must be built first |
| `wd` | dir (relative to repo root) the `acquire` recipe runs in — defaults to `.` |
| `deps` | another entry's key that must be built first |
| `acquire` | shell recipe to build the artifact |

Notes for editing this file: `acquire` is read by key with a separate `yq` call rather than through the main `@tsv` row, because `@tsv` CSV-quotes any field containing `"` and mangles shell quoting. Use `"$CC"` (double quotes) — single quotes prevent expansion. Chain steps with `&&` so a failed `configure` doesn't run `make`. Entries with no `src`/`dest` are skipped as stubs.

**Patch system** (`sys/patches/`): Patches are managed with `quilt`. The `series` file controls apply order: `telnet.patch` → `pwd.patch` → `set_system_info.patch` → `entware.patch`. Patches live in `sys/patches/` and are applied against the extracted rootfs.

**Runtime scripts** (`sys/util/`): Shell scripts intended to run on the device itself. `alterna.sh` handles first-boot Entware setup — it bind-mounts `/log/0/hd/opt` over `/opt` for persistence across reboots, then installs Entware (armv7sf-k3.2) on first boot.

**Tooling** (`tooling/`): Python (run via `uv`) handles firmware parsing. `parts.py` defines `FirmwarePart` offsets for the 2104 firmware; `extract.py` slices and writes each part to `build/`. `fstable.py` writes the partition table into the RSUp header from `build/fsfollow`; `crc.py` computes and injects the uImage body, uImage header, and RSUp header checksums — it requires `-m <model>` (`2104` or `2108`) and exits 1 without it.

**Build output**: Extracted parts land in `build/rootfs/`, repacked parts in `build/roots/`, and the final image is `build/update.bin`. The `rootfs/mkimg.rootfs` script (from stock tooling) can repackage a rootfs directory into jffs2, cramfs, or yaffs2 images using standard mtd tools.

## Deploying to a device

The stock path is U-Boot's `CheckUpgrade`, which validates an RSUp image (magic, version, CRC) and flashes per-partition, skipping any part whose length is zero — so a rootfs-only update is expressible in the format. It loads from USB (`fatload`) or `sf read` of offsets inside mtd0.

Stock firmware has **no `fw_setenv`/`fw_printenv`, no `flashcp`, no `mtd_debug`** — only `dd`, `nc`, `wget`, `md5sum`, `base64`, busybox. Writing mtd2 directly with `dd` works, with two caveats:

- **Pad the image to a 64K erase-block multiple.** `mtdblock` silently drops a trailing partial erase block: `dd` reports success and the full byte count, but the last block reads back as `0xff`. This produces a truncated, unbootable squashfs. Pad with `0xff` — squashfs only reads up to the size in its superblock.
- **Always read back and compare md5 before rebooting.** The write reporting `rc=0` is not evidence it landed.

Back up the partition first (`dd if=/dev/mtd2ro`) and never write mtd0 — a bad boot-partition write is unrecoverable without a hardware programmer.

## Device gotchas

- `/opt` is a bind-mount of `/log/0/hd/opt` (see `alterna.sh`), and `PATH` puts `/opt/sbin:/opt/bin` **first**. An Entware binary in `/opt/bin` therefore shadows the same-named binary in `/usr/bin` — bare `curl` may not be the one this project installs. Call `/usr/bin/curl` explicitly when it matters.
- The login shell exports `LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/mnt/lib`. When testing whether a binary links correctly, use `env -u LD_LIBRARY_PATH` — otherwise the test proves nothing.
- uClibc 0.9.33.2, no `/etc/ld.so.conf` and no `ldd`. The loader does search `/lib` and `/usr/lib` by default, so cross-compiled libraries installed to `/usr/lib` need no `RPATH`; pass `--prefix=/usr` so libtool doesn't bake in a `/usr/local/lib` one.
- `/log/0` is a large ext filesystem on the internal HDD — the right place to stage files, and it survives reboots.
