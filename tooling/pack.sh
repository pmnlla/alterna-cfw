#!/bin/bash -x
set -euo pipefail

BLOCKSIZE=65536
COMPRESSION="xz"
VERSION=$(git describe --always --dirty)

in_array () {
    local somearray=${1}[@]
    shift
    for SEARCH_VALUE in "$@"; do
        FOUND=false
        for ARRAY_VALUE in ${!somearray}; do
            if [[ $ARRAY_VALUE == $SEARCH_VALUE ]]; then
                FOUND=true
                break
            fi
        done
        if ! $FOUND; then
            return 1
        fi
    done
    return 0
}

prereq() {
    for file in "${ROOTS[@]}"; do
        if [ -f "roots/$file" ]; then
            ../tooling/glorify.sh alert info "$file exists.";
        else
            ../tooling/glorify.sh alert info "$file is missing. Re-extracting";
            mkdir roots;
            cp ../firmware.bin .
            ln -s ../tooling .
            mise x -- uv run tooling/extract.py 2104 firmware.bin roots;
            break;
        fi
    done;
    if [ ! -d "../rootfs" ]; then
        ../tooling/glorify.sh alert info  "Rootfs not found. Extracting...";
        unsquashfs -d ../rootfs roots/Squashfs_rootfs_1;
    fi
}

include() {
    built=()
    while IFS=$'\t' read -r key src dest needs deps wd; do
        if [[ "$src" == "NULL" || "$dest" == "NULL" ]]; then
            ../tooling/glorify.sh alert info  "Skipping $key: stub entry (no src/dest)"
            continue
        fi
        in_array_result=0
        in_array built $deps || in_array_result=$?
        if [[ "$needs" == "NULL" && ( "$deps" == "NULL" || $in_array_result -eq 0 ) ]]; then # this is an artifact with no additional requirements!
            cp -d ../$src rootfs$dest
            ../tooling/glorify.sh alert info  "Copied $src to $dest"
            built+=($key)
        elif [[ $needs == "selfAcquire"  && ( "$deps" == "NULL" || $in_array_result -eq 0 ) ]]; then
            # fetched by key, not via @tsv: shell quoting in acquire survives intact
            acquire=$(yq ".inclusion.$key.acquire" ../sys/inclusions.yaml)
            # acquire runs in the artifact's own source tree, not build/
            if ! (cd "../$wd" && bash -c "$acquire"); then
                ../tooling/glorify.sh alert error  "DID NOT BUILD $src: acquire failed!"
                exit 1
            fi
            cp -d ../$src rootfs$dest
            ../tooling/glorify.sh alert info  "Copied $src to $dest"
            built+=($key)
        else
            ../tooling/glorify.sh alert error  "DID NOT BUILD $src: deps missing!"
            exit 1
        fi    
    done < <(yq '.inclusion | to_entries[] | [.key, (.value.src // "NULL"), (.value.dest // "NULL"), (.value.needs // "NULL"), (.value.deps // "NULL"), (.value.wd // ".")] | @tsv' ../sys/inclusions.yaml)
}

pack_squash() {
    rm -rf rootfs || true;
    rm roots/4_Squashfs_rootfs || true;
    cp -r ../rootfs .;
    echo $VERSION > rootfs/etc/hd/version
    ../tooling/glorify.sh alert info  "Packing inclusions..."
    include
    ../tooling/glorify.sh alert info "Creating root squashfs...."
    mksquashfs rootfs/. roots/4_Squashfs_rootfs -comp $COMPRESSION -b $BLOCKSIZE
}

mkdir -p build;
cd build;
prereq 

if [ "$1" = "squash" ]; then
    pack_squash
elif [ "$1" = "rsup" ]; then
    pack_squash
    rm update.bin
    echo "{" > ./fsfollow
    for i in $(ls roots/); do
        cat roots/$i >> update.bin;
        SIZE=$(stat -c %s roots/$i);
        OFFSET=$(echo "obase=16; $(($(stat -c %s update.bin)-$SIZE))" | bc);
        SIZE=$(echo "obase=16; $SIZE" | bc);
        ../tooling/glorify.sh alert info "wrote $i - size 0x$SIZE - offset 0x$OFFSET";
        echo "{'$i', '$OFFSET', '$SIZE'}," >> ./fsfollow
    done
    echo "{'EOF', '0', '0'}" >> ./fsfollow # since we assume every entry isn't the last, i need this block to make json not shit itself. can you tell this is budged together? i can't!
    echo "}" >> ./fsfollow
    ../tooling/glorify.sh alert info "Packed!";
    #for i in "${ROOTS_POST[@]}"; do
    #    cat roots/$i >> update.bin;
    #    echo "Wrote $i to update.bin";
    #done;
fi

