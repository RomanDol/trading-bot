const serverName = document.querySelector('meta[name="server-name"]').content;
if (serverName && !window.location.hash) {
    window.location.hash = serverName;
}