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

  $( function() { 
    //function used in forms:
    // the object which controls status of other objects
    // should have class "testForNegative" and obligatory
    // one or more classes:
    // ifNegativeDisable@<classNameToDisable>
    // ifNegativeEnable@<classNameTOEnable>
    $( ".testForNegative" ).on('change', function() {
      var classes = this.className.split(" ");
      var onOff = (this.value < 0);
      classes.forEach( function(name){
        if (name.startsWith('ifNegativeDisable@')) {
          var cname = "." + name.substring(18);
          if ( !onOff ) {
            $(cname).prop('disabled', false);
          } else {
            $(cname).prop('disabled', true);
          }
        } else if (name.startsWith('ifNegativeEnable@')) {
          var cname = "." + name.substring(17);
          if ( onOff ) {
            $(cname).prop('disabled', false);
          } else {
            $(cname).prop('disabled', true);
          }
        }
      });
    });
    // Check conditions at the beggining:
    $( ".testForNegative" ).trigger("change");
  });

  $( function() {
      // js wrapper for url transitions for buttons etc.
      $( ".urlChanger" ).on('click', function() {
         var classes = this.className.split(" ");
         classes.forEach( function(name) {
            if (name.startsWith('url@')) {
               var url = atob(name.substring(4));
           window.location=url;
        }
         })
      });
  });

    $( function() {
        $( ".plotHighlight" ).hover( function() {
         var classes = this.className.split(" ");
         classes.forEach( function(name) {
            if (name.startsWith('highlightCurve@')) {
               var number = name.substring(15);
               var cname = 'curve_' + number;
               Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_width = 8;
               Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_color = 'red';
            }
         }); 
        }, function() {
         var classes = this.className.split(" ");
         classes.forEach( function(name) {
            if (name.startsWith('highlightCurve@')) {
               var number = name.substring(15);
               var cname = 'curve_' + number;
               Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_width = 2;
               Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_color = 'blue';
            }
         }); 
        });
    });
</script>
