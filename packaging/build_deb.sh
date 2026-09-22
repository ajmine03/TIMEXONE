#!/usr/bin/env bash
set -e

# Change directory to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="0.2.0"
PKG_NAME="focusflow"
PKG_FULL="${PKG_NAME}_${VERSION}-1_all"
DIST_DIR="${ROOT_DIR}/packaging/dist"
STAGE_DIR="${DIST_DIR}/${PKG_FULL}"

echo "==> Building Debian package for ${PKG_NAME} v${VERSION}..."

# Clean old build
rm -rf "${STAGE_DIR}"
mkdir -p "${DIST_DIR}"

# Create Debian directory layout
mkdir -p "${STAGE_DIR}/DEBIAN"
mkdir -p "${STAGE_DIR}/usr/bin"
mkdir -p "${STAGE_DIR}/usr/lib/${PKG_NAME}"
mkdir -p "${STAGE_DIR}/usr/share/applications"
mkdir -p "${STAGE_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${STAGE_DIR}/usr/share/doc/${PKG_NAME}"

# 1. Copy Application Code & Assets
cp -r "${ROOT_DIR}/focusflow" "${STAGE_DIR}/usr/lib/${PKG_NAME}/"
cp -r "${ROOT_DIR}/assets" "${STAGE_DIR}/usr/lib/${PKG_NAME}/"
cp "${ROOT_DIR}/run.py" "${STAGE_DIR}/usr/lib/${PKG_NAME}/"

# Clean any pycache in staging
find "${STAGE_DIR}/usr/lib/${PKG_NAME}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${STAGE_DIR}/usr/lib/${PKG_NAME}" -name "*.pyc" -delete 2>/dev/null || true

# 2. Create Executable Wrapper in /usr/bin
cat <<'EOF' > "${STAGE_DIR}/usr/bin/focusflow"
#!/usr/bin/env bash
exec /usr/bin/python3 /usr/lib/focusflow/run.py "$@"
EOF
chmod 755 "${STAGE_DIR}/usr/bin/focusflow"

# 3. Copy Desktop Entry and Icons
cp "${ROOT_DIR}/packaging/focusflow.desktop" "${STAGE_DIR}/usr/share/applications/"
cp "${ROOT_DIR}/assets/focusflow.svg" "${STAGE_DIR}/usr/share/icons/hicolor/scalable/apps/"

# 4. Copy Documentation & Copyright
cp "${ROOT_DIR}/packaging/debian/copyright" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/"
cp "${ROOT_DIR}/packaging/debian/changelog" "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/changelog.Debian"
gzip -9 -n "${STAGE_DIR}/usr/share/doc/${PKG_NAME}/changelog.Debian"

# 5. Copy DEBIAN control file
cp "${ROOT_DIR}/packaging/debian/control" "${STAGE_DIR}/DEBIAN/control"

# 6. Create postinst script (updates icon/desktop caches)
cat <<'EOF' > "${STAGE_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if which update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q || true
    fi
    if which gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q /usr/share/icons/hicolor || true
    fi
fi
exit 0
EOF
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/DEBIAN/postinst"

# 7. Build .deb package
DEB_FILE="${DIST_DIR}/${PKG_FULL}.deb"
dpkg-deb --build --root-owner-group "${STAGE_DIR}" "${DEB_FILE}"

echo "==> Successfully created Debian package: ${DEB_FILE}"
echo "==> Package info:"
dpkg-deb -I "${DEB_FILE}"
echo "==> Package contents:"
dpkg-deb -c "${DEB_FILE}"
