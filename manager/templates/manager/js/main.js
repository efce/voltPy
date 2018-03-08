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

function voltpy_loading_start(text) {
    window.scrollTo(0, 0);
    $('body').css('overflow','hidden');
    $('#voltpy-loading').addClass('loading-cover');
    $('#voltpy-loading').css('line-height', $('#voltpy-loading').css('height'));
    $('#voltpy-loading').text(text);
}
function voltpy_loading_done()
{
    $('#voltpy-loading').css('display','none');
    $('body').css('overflow','scroll');
}

// Function used for communication between the page and server, with loading text.
function voltpy_query(url, object, funcOnReturn) {
    object['csrfmiddlewaretoken'] = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    voltpy_loading_start('Loading ...');
    function retFun(data) {
        funcOnReturn(data);
        voltpy_loading_done();
    }
    $.post(url, object).done(retFun);
};

function queryServer(url, object, plot=null, lineData=null, cursors=null) {
    //TODO: partial 
    function processReplyPartial (data) {
        processJSONReply(data, plot, lineData, cursors);
    }
    voltpy_query(url, object, processReplyPartial);
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

$( function() {
    $(".closeX").on('click', function(e) {
        $(e.target).closest('div').css('display', 'none');
    });
});

// This is used in various forms. Magic classes names.
$( function() { 
    //function used in forms:
    // the object which controls status of other objects
    // should have class "_voltJS_testForNegative@" and obligatory
    // one or more classes:
    // _voltJS_ifNegativeDisable@<classNameToDisable>
    // _voltJS_ifNegativeEnable@<classNameTOEnable>
    iclassDisable = '_voltJS_ifNegativeDisable@'
    iclassEnable = '_voltJS_ifNegativeEnable@'
    $( '._voltJS_testForNegative' ).on('change', function() {
        var classes = this.className.split(" ");
        var onOff = (this.value < 0);
        classes.forEach( function(name){
            if (name.startsWith(iclassDisable)) {
                var cname = "." + name.substring(iclassDisable.length);
                if ( !onOff ) {
                    $(cname).prop('disabled', false);
                } else {
                    $(cname).prop('disabled', true);
                }
            } else if (name.startsWith(iclassEnable)) {
                var cname = '.' + name.substring(iclassEnable.length);
                if ( onOff ) {
                    $(cname).prop('disabled', false);
                } else {
                    $(cname).prop('disabled', true);
                }
            }
        });
    });
    // Check conditions at the beggining:
    $( '._voltJS_testForNegative' ).trigger('change');
});

$( function() {
    // js wrapper for url transitions for buttons etc. Magic class names.
    var iclassUrl = '_voltJS_url@'
    $( '._voltJS_urlChanger' ).on('click', function() {
        var classes = this.className.split(" ");
        classes.forEach( function(name) {
            if (name.startsWith(iclassUrl)) {
                var url = atob(name.substring(iclassUrl.length));
                window.location=url;
            }
        })
    });
});

$( function() {
    $( '._voltJS_backButton' ).on('click', function(e) {
        e.preventDefault();
        var theform = $(e.target).closest('form');
        var addVal = $('<input>').attr('type', 'hidden').attr('name', '_voltJS_backButton').val(1);
        theform.append(addVal);
        theform.submit();
    });
});

// This is used in analytesTable, when selecting analyte. Magic classes names.
$( function() {
    window.voltPy1.ChangeDispCurrent = -1;
    $( '._voltJS_ChangeDispValue' ).on('change', function() {
        var value = this.value;
        if (value == window.voltPy1.ChangeDispCurrent)
            return;
        
        if ( window.voltPy1.ChangeDispCurrent != -1 ) {
            var classToHide = '_voltJS_changeValue_' + window.voltPy1.ChangeDispCurrent;
            $( '.' + classToHide ).css('display', 'none');
        }
        if (value != -1 ) {
            var classToShow = '_voltJS_changeValue_' + value;
            $( "." + classToShow ).css('display', 'table-cell');
        }
        window.voltPy1.ChangeDispCurrent = value;
    });
});

$( function() {
    // TODO: find some nicer way to change Bokeh plots colors
    var iclass = '_voltJS_highlightCurve@'
    $( '._voltJS_plotHighlight' ).hover( function() { // on hover in
        $(this).css('background-color', 'red');
        $(this).css('color', 'white');
        var classes = this.className.split(' ');
        classes.forEach( function(name) {
            if (name.startsWith(iclass)) {
                var number = name.substring(iclass.length);
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
            if (name.startsWith(iclass)) {
                var number = name.substring(iclass.length);
                var cname = 'curve_' + number;
                Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_width = 2;
                Bokeh.documents[0]._all_models_by_name._dict[cname].glyph.line_color = 'blue';
            }
        }); 
    });
});

$( function() {
    $( '._voltJS_toggleShow' ).on('change', function(e) {
        toggleShow(e.target);
    });
});
function toggleShow(e) {
    $(e.target).next('._voltJS_toShow' ).toggleClass('invisible visible');
}

$( function() {
    $( '._voltJS_Disable' ).on( 'change', function(e) {
        $(e.target).parent().find('._voltJS_disableContainer').find('._voltJS_toDisable').prop('checked', this.checked);
        $(e.target).parent().find('._voltJS_disableContainer').find('._voltJS_toDisable').prop('disabled', this.checked);
    });
    $('._voltJS_Expand').on('click', function (e) {
        $(e.target).next('._voltJS_expandContainer').children('._voltJS_toExpand').toggleClass('visible invisible');
        e.preventDefault();
    });
});
</script>
