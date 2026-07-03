# Cypress GUI in a browser tab — zero host installs (Bonsai™ doctrine).
# cypress/included + Xvfb virtual display + x11vnc + noVNC: `make e2e_watch`
# serves the interactive Cypress runner at http://localhost:6080/vnc.html.
# BACKLOG: replace VNC transport with the WebRTC alternative (TODO.md).
# 15.x, NOT the 13.x devDep major: Cypress 13 bundles Chromium 118 whose
# ReadableStream is not async-iterable — the app's streaming path throws.
FROM cypress/included:15.18.0

# scrot: one-command screenshots of the virtual display for debugging
# (docker exec sage-e2e-watch scrot /tmp/s.png)
RUN apt-get update && \
    apt-get install -y --no-install-recommends x11vnc novnc websockify fluxbox scrot && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Fluxbox: maximize every window on this single-purpose display — the Cypress
# launchpad AND the spec-runner browser open fullscreen, no manual resizing.
RUN mkdir -p /root/.fluxbox && \
    printf '[app] (name=.*)\n  [Maximized] {yes}\n[end]\n' > /root/.fluxbox/apps

# Sage branding: overwrite the Cypress logo bytes in the GUI's hashed assets
# (filename/hash unchanged — the app loads them by name). Cosmetic, dev-only.
COPY sage-logo-64.png /tmp/sage-logo-64.png
RUN find /root/.cache/Cypress -type f \( -name 'cypress_s-*.png' -o -name 'cypress-dark-*.png' \) \
      -exec cp /tmp/sage-logo-64.png {} \; && \
    echo "logo swapped in: $(find /root/.cache/Cypress -name 'cypress_s-*.png' | wc -l) + $(find /root/.cache/Cypress -name 'cypress-dark-*.png' | wc -l) assets"

# Same for the noVNC page: its "logo" is styled text (no/VNC) + a favicon set.
# S-hex image + title on the connect screen and control bar, favicons swapped
# byte-for-byte (browsers rescale the 64px happily).
RUN cp /tmp/sage-logo-64.png /usr/share/novnc/app/images/sage-logo.png && \
    for f in /usr/share/novnc/app/images/icons/novnc-ios-*.png; do cp /tmp/sage-logo-64.png "$f"; done && \
    cp /tmp/sage-logo-64.png /usr/share/novnc/app/images/icons/novnc.ico && \
    sed -i 's|<title>noVNC</title>|<title>Sage.is AI — e2e watch</title>|' /usr/share/novnc/vnc.html && \
    sed -i 's|<h1 class="noVNC_logo" translate="no"><span>no</span><br>VNC</h1>|<h1 class="noVNC_logo" translate="no" style="text-align: center;"><img src="app/images/sage-logo.png" alt="Sage.is" style="height:84px;margin-bottom: 0.4em;border-radius: 0.6em;"><br>Sage.is e2e</h1>|' /usr/share/novnc/vnc.html && \
    sed -i 's|<p class="noVNC_logo" translate="no"><span>no</span>VNC</p>|<p class="noVNC_logo" translate="no" style="text-align: center;">Sage.is e2e</p>|' /usr/share/novnc/vnc.html && \
    grep -c "Sage.is" /usr/share/novnc/vnc.html

# Match the logo type/color to the AI-UI itself (Archivo, black) instead of
# noVNC's stock yellow Orbitron.
COPY sage-brand.css /usr/share/novnc/app/styles/sage-brand.css
COPY sage-archivo.ttf /usr/share/novnc/app/styles/sage-archivo.ttf
RUN sed -i 's|</head>|<link rel="stylesheet" href="app/styles/sage-brand.css">\n</head>|' /usr/share/novnc/vnc.html

COPY entrypoint.sh /watch-entrypoint.sh
RUN chmod +x /watch-entrypoint.sh
ENTRYPOINT ["/watch-entrypoint.sh"]
