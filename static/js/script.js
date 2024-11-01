document
  .getElementById("fetch-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const useCache = document.getElementById("use-cache").checked;
    const progress = document.getElementById("progress");
    const result = document.getElementById("result");
    const rawDataButton = document.getElementById("raw-data");
    const downloadJsonButton = document.getElementById("download-json");
    const viewWebButton = document.getElementById("view-web");

    progress.textContent = "Fetching data...";
    result.textContent = "";
    rawDataButton.disabled = true;
    downloadJsonButton.disabled = true;
    viewWebButton.disabled = true;

    fetch(`/fetchdata/${username}/raw?cache=${useCache}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          progress.textContent = "Error fetching data!";
          result.textContent = data.error;
        } else {
          progress.textContent = "Data fetched successfully!";
          rawDataButton.disabled = false;
          downloadJsonButton.disabled = false;
          viewWebButton.disabled = false;

          rawDataButton.onclick = () =>
            window.open(`/fetchdata/${username}/raw`, "_blank");
          downloadJsonButton.onclick = () =>
            window.open(`/fetchdata/${username}/download`, "_blank");
          viewWebButton.onclick = () =>
            window.open(`/fetchdata/${username}/web-view`, "_blank");
        }
      })
      .catch((error) => {
        progress.textContent = "Error fetching data!";
        result.textContent = error.toString();
      });
  });
