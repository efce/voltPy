<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
{% include "./bokeh.js" %}
<script type="text/javascript">

$( function() {
 window.voltPy1 = {};
});

// Implementation of sleep. Used during reload, to allow the server some time for processing.
function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
};

// Function used for communication between the page and server, with loading text.
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

// This is main JS function for sending and processing JSON.
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

// This is used in various forms. Magic classes names.
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
    // js wrapper for url transitions for buttons etc. Magic class names.
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

// This is used in analytesTable, when selecting analyte. Magic classes names.
$( function() {
    window.voltPy1.atChangerCurrent = -1;
    $( ".atChanger" ).on('change', function() {
        var value = this.value;
        if (value == window.voltPy1.atChangerCurrent)
            return;
        
        if ( window.voltPy1.atChangerCurrent != -1 ) {
            var classToHide = "atAnalyte" + window.voltPy1.atChangerCurrent;
            $( "." + classToHide ).css('display', 'none');
        }
        if (value != -1 ) {
            var classToShow = "atAnalyte" + value;
            $( "." + classToShow ).css('display', 'table-cell');
        }
        window.voltPy1.atChangerCurrent = value;
    });
});

$( function() {
    // TODO: find some nicer way to change Bokeh plots colors
    $( ".plotHighlight" ).hover( function() { // on hover in
        $(this).css('background-color', 'red');
        $(this).css('color', 'white');
        var classes = this.className.split(" ");
        classes.forEach( function(name) {
            if (name.startsWith('highlightCurve@')) {
                var number = name.substring(15);
                var cname = 'curve_' + number;
                Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_width = 8;
                Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_color = 'red';
            }
        }); 
    }, function() { // on hover out
        var classes = this.className.split(" ");
        $(this).css('background-color', 'white');
        $(this).css('color', 'black');
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

$( function() {
    $( '._voltJS_Disable' ).on( 'change', function(e) {
        $(e.target).parent().find('ul').find('._voltJS_toDisable').prop('checked', this.checked);
        $(e.target).parent().find('ul').find('._voltJS_toDisable').prop('disabled', this.checked);
    });
    $('._voltJS_Expand').on('click', function (e) {
        $(e.target).next('._voltJS_expandContainer').children('._voltJS_toExpand').toggleClass('visible invisible');
        e.preventDefault();
    });
});
</script>
