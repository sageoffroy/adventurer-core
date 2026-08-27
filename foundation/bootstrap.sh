#!/usr/bin/env bash
set -euo pipefail

CORE_REPO="https://github.com/azerothcore/azerothcore-wotlk.git"
CORE_COMMIT="4f9040b4f354c052763cbb554b06031b8caafa04"

TIME_REPO="https://github.com/dunjeon/mod-TimeIsTime.git"
TIME_COMMIT="abfb3a7a031c168c481642604c1389a5d92f4499"
ALE_REPO="https://github.com/azerothcore/mod-ale.git"
ALE_COMMIT="9eeb1f3c47a81291548874fa4be2f4cde35e2ec3"
AOE_REPO="https://github.com/azerothcore/mod-aoe-loot.git"
AOE_COMMIT="b5c663572d936985c19dc8b499ecea60e1da570d"

# Existing clean AzerothCore tree used by Aventureros.
CORE_DIR="${1:-$HOME/aventurerosdeazeroth}"
BUILD_DIR="$CORE_DIR/build-foundation-v1"
BUILD_CORES="${BUILD_CORES:-$(nproc)}"
if (( BUILD_CORES > 1 )); then
    BUILD_CORES=$((BUILD_CORES - 1))
fi

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: required command not found: $1" >&2
        exit 1
    }
}

for cmd in git cmake make clang clang++ nproc; do
    require_cmd "$cmd"
done

if [[ ! -d "$CORE_DIR/.git" ]]; then
    echo "ERROR: expected an existing AzerothCore git tree at: $CORE_DIR" >&2
    exit 1
fi

if [[ -n "$(git -C "$CORE_DIR" status --porcelain)" ]]; then
    echo "ERROR: core tree has local changes: $CORE_DIR" >&2
    echo "Refusing to change commits until the clean base is actually clean." >&2
    git -C "$CORE_DIR" status --short >&2
    exit 1
fi

echo "==> Pinning existing AzerothCore tree to $CORE_COMMIT"
if ! git -C "$CORE_DIR" cat-file -e "$CORE_COMMIT^{commit}" 2>/dev/null; then
    git -C "$CORE_DIR" fetch "$CORE_REPO" "$CORE_COMMIT"
fi
git -C "$CORE_DIR" checkout --detach "$CORE_COMMIT"

mkdir -p "$CORE_DIR/modules"

install_module() {
    local repo="$1"
    local commit="$2"
    local dest="$3"

    echo "==> Installing $(basename "$dest") @ $commit"

    if [[ -e "$dest" && ! -d "$dest/.git" ]]; then
        echo "ERROR: module destination exists but is not a git repository: $dest" >&2
        exit 1
    fi

    if [[ ! -d "$dest/.git" ]]; then
        git clone "$repo" "$dest"
    elif [[ -n "$(git -C "$dest" status --porcelain)" ]]; then
        echo "ERROR: module has local changes: $dest" >&2
        exit 1
    fi

    if ! git -C "$dest" cat-file -e "$commit^{commit}" 2>/dev/null; then
        git -C "$dest" fetch "$repo" "$commit"
    fi
    git -C "$dest" checkout --detach "$commit"
}

install_module "$TIME_REPO" "$TIME_COMMIT" "$CORE_DIR/modules/mod-TimeIsTime"
install_module "$ALE_REPO" "$ALE_COMMIT" "$CORE_DIR/modules/mod-ale"
install_module "$AOE_REPO" "$AOE_COMMIT" "$CORE_DIR/modules/mod-aoe-loot"

echo "==> Configuring isolated foundation build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
cmake ../ \
    -DCMAKE_INSTALL_PREFIX="$CORE_DIR/env/dist/" \
    -DCMAKE_C_COMPILER=/usr/bin/clang \
    -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
    -DWITH_WARNINGS=1 \
    -DTOOLS_BUILD=all \
    -DSCRIPTS=static \
    -DMODULES=static

echo "==> Building with $BUILD_CORES job(s)"
make -j"$BUILD_CORES"
make install

echo
echo "Foundation build complete."
echo "Core tree:   $CORE_DIR"
echo "Core:        $CORE_COMMIT"
echo "TimeIsTime:  $TIME_COMMIT"
echo "ALE:         $ALE_COMMIT"
echo "AoE Loot:    $AOE_COMMIT"
echo "Build dir:   $BUILD_DIR"
echo "Install:     $CORE_DIR/env/dist"
