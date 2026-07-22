# Alterna
Custom firmware for the Lorex LHA2104, LHA2108/LC, and possibly other Raysharp derivatives.

## Yeah, so what do I get from this?

A bunch of shit. notably:
- SSH and telnet directly into your DVR
- Package management, powered by entware - the same package manager you'll find on your router. It's pretty handy.
- Custom init scripts, in /opt/etc/init.d - to go along with package management. Entware drops init scripts here.
- Hostnames, because for some reason the DVRs don't set their own hostname. This firmware sets it to match the MAC address from the DVR so you can tell them apart. 
- The only limit is your imagination :3c

I personally use it for go2rtc, since the client for these DVRs doesn't work anymore on most Android devices, or any modern Mac.

## Building from Source

**Preliminary: Set up dependencies.**

This project depends on [mise-en-place](https://mise.jdx.dev) for dependency management, tooling, and build scripts. Set it up with:

```
curl https://mise.run | sh # piping unknown scripts to shell always carries a risk. 
```

Then clone the repository. (this is not a tutorial on how to use git :p )

Next, grab a copy of a **STOCK** firmware blob for your DVR. They're distributed by Lorex [here](https://www.lorextechnology.com/images/supportimages/supportarticles/firmware/Lorex_DVR_NVR_Firmware.pdf), drop it into the repository, and let's get going.

### Ok, so, now what?

This project uses mise-en-place tasks to make building easier. They're located in the mise-tasks/ folder. Run them with `mise r <task>`

The tasks may reference tooling in the tooling/ folder.

The general flow is, (mise) extract -> set_patchset -> load -> build, which:

1. Extracts the firmware
2. Selects the patchset you wish to apply (right now, the only available option is rootfs.)
3. Loads the patches into the rootfs
4. Packs it all nice and tidy into an update blob, bumps the version, and solves the CRCs.

After which, you can copy build/update.signed and update your DVR from it through the usual UI flow. 

| Task | Arguments | Description |
|------|-----------|-------------|
| `mise run extract <blob> [dont-unsquash-the-filesystem]` | `<blob>`: firmware image; optional 2nd arg skips unsquashing | Auto-detects model (2104/2108) from the blob header, slices parts into `build/roots/`, then unsquashes the `*_rootfs` and `*_app` images into `rootfs/` and `appfs/`. |
| `mise run set_patchset <name>` | `<name>`: patchset under `sys/patches/`; empty wipes `.pc/` | Records the active patchset in `.pc/.hd_patchset` for subsequent quilt tasks. |
| `mise run new <name>` | `<name>`: patch file name (`.patch` appended) | Creates a new quilt patch in the active patchset. Follow with `quilt add <file>`. |
| `mise run load` | — | Applies all patches in the active patchset (`quilt update` + `quilt push -a`). |
| `mise run seal` | — | Refreshes the current patch header/diff, then pops all patches (`quilt pop -a`), reverting rootfs to stock. |
| `mise run build` | — | The big build: `pack.sh rsup`, rewrites the partition table (`fstable.py`), then fixes the CRC (`crc.py`) → `build/update.bin`. |
| `mise run clean` | — | Removes `rootfs/`, `appfs/`, `build/`, and `.pc/`. |

**Keep in mind the name is sensitive, and is how the raysharp updater determines if the firmware is applicable to your DVR or not. Rename your CFW blob to match the stock blod.**

## I bricked it!

You're fine. Take a deep breath.

Then, grab a Phillips screwdriver, a USB drive, and a USB-to-UART adapter.

Hook up the USB-UART adaptea