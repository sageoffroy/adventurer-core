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

CORE_DIR="${1:-$HOME/aventurerosdeazeroth-v2}"
BUILD_CORES="${BUILD_CORES:-$(nproc)}"
if (( BUILD_CORES > 1 )); then
    BUILD_CORES=$((BUILD_CORES - 1))
fi

if [[ -e "$CORE_DIR" ]]; then
    echo "ERROR: destination already exists: $CORE_DIR" >&2
    echo "Refusing to overwrite an existing server tree." >&2
    exit 1
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

echo "==> Cloning pinned AzerothCore base"
git clone --branch master --single-branch "$CORE_REPO" "$CORE_DIR"
git -C "$CORE_DIR" checkout --detach "$CORE_COMMIT"

mkdir -p "$CORE_DIR/modules"

clone_module() {
    local repo="$1"
    local commit="$2"
    local dest="$3"
    echo "==> Installing $(basename "$dest") @ $commit"
    git clone "$repo" "$dest"
    git -C "$dest" checkout --detach "$commit"
}

clone_module "$TIME_REPO" "$TIME_COMMIT" "$CORE_DIR/modules/mod-TimeIsTime"
clone_module "$ALE_REPO" "$ALE_COMMIT" "$CORE_DIR/modules/mod-ale"
clone_module "$AOE_REPO" "$AOE_COMMIT" "$CORE_DIR/modules/mod-aoe-loot"

echo "==> Configuring build"
mkdir -p "$CORE_DIR/build"
cd "$CORE_DIR/build"
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
echo "Core:       $CORE_COMMIT"
echo "TimeIsTime: $TIME_COMMIT"
echo "ALE:        $ALE_COMMIT"
echo "AoE Loot:   $AOE_COMMIT"
echo "Install:    $CORE_DIR/env/dist"
