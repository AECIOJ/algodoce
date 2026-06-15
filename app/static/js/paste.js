document.addEventListener('paste', function(e) {
  var fileInput = document.querySelector('input[type="file"][name="imagem"]');
  if (!fileInput) return;
  var item = e.clipboardData && e.clipboardData.items[0];
  if (item && item.type.startsWith('image/')) {
    var file = item.getAsFile();
    var dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    var label = fileInput.closest('.mb-3');
    if (label) {
      var existing = label.querySelector('.paste-indicator');
      if (!existing) {
        var badge = document.createElement('span');
        badge.className = 'paste-indicator badge bg-success ms-2';
        badge.textContent = 'Imagem colada!';
        fileInput.parentNode.appendChild(badge);
        setTimeout(function() { badge.remove(); }, 3000);
      }
    }
  }
});
