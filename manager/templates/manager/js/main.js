<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
{% include "./bokeh.js" %}
<script type="text/javascript">
  function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
  };

  function queryServer(url, object, plot=null, lineData=null, cursors=null) {
    alert('querying server');
    window.scrollTo(0, 0);
    $('body').css('overflow','hidden');
    $('#voltpy-loading').addClass('loading-cover');
    $('#voltpy-loading').css('line-height', $('#voltpy-loading').css('height'));
    $('#voltpy-loading').text(' Loading ... ');
    $.post(url, object).done(
        function(data) {
            processJSONReply(data, plot, lineData, cursors);
            $('#voltpy-loading').css('display','none');
            $('body').css('overflow','scroll');
        }
    );
  };

  function processJSONReply(data, plot='',lineData='',cursors='') {
    switch (data.command) {
    case 'none':
      return;
    case 'reload':
      sleep(500).then(()=>{location.reload();});
      break;
    case 'redirect':
      location = data.location;
      break;
    case 'setCursor':
      cursors[data.number].location = parseFloat(data.x);
      cursors[data.number].line_alpha = 1;
      break;
    case 'setLineData':
      var xv = lineData.data['x'];
      var yv = lineData.data['y'];
      for (i = 0; i < data.x.length; i++) {
        xv[i] = data.x[i];
        yv[i] = data.y[i];
      }
      xv.length = data.x.length;
      yv.length = data.x.length;
      lineData.trigger('change');
      break;
    case 'removeLine':
      lineData.x = [];
      lineData.y = [];
      lineData.trigger('change');
      break;
    case 'removeCursor':
      cursors[data.number].line_alpha = 0;
      break;
    case 'changeColor':
    default:
      alert('Not implemented...');
    }
  };
</script>