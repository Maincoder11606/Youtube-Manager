
document.addEventListener("DOMContentLoaded", function() {
  const form = document.getElementById("video-search-form");
  const videoGallery = document.getElementById("video-gallery");

  form.addEventListener("submit", function(event) {
    event.preventDefault();
    const searchQuery = document.getElementById("search-query").value;
    fetchVideos(searchQuery);
  });

  function fetchVideos(searchQuery) {
    const apiKey = 'YOUR_YOUTUBE_API_KEY';
    const url = `https://www.googleapis.com/youtube/v3/search?key=${apiKey}&part=snippet&q=${searchQuery}&type=video`;

    fetch(url)
      .then(response => response.json())
      .then(data => {
        videoGallery.innerHTML = '';  // Clear existing videos
        data.items.forEach(item => {
          const videoId = item.id.videoId;
          const videoTitle = item.snippet.title;
          const videoThumbnail = item.snippet.thumbnails.default.url;

          const videoElement = document.createElement("div");
          videoElement.classList.add("video-item");
          videoElement.innerHTML = `
            <div class="video-thumbnail">
              <iframe width="560" height="315" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allowfullscreen></iframe>
            </div>
            <p class="video-title">${videoTitle}</p>
          `;

          videoGallery.appendChild(videoElement);
        });
      })
      .catch(error => console.error("Error fetching videos:", error));
  }
});

