$( function() {
    window.voltPy1 = {}
});

// Implementation of sleep. Used during reload, to allow the server some time for processing.
function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time))
};

function searchDataset(txt, funcResults) {
    url = '/manager/ajax/search-dataset/';
    csfr = $("{% csrf_token %}").val();
    object = {
        'search': txt,
        'csrfmiddlewaretoken': csfr,
    };
    $.post(url, object).done(funcResults);
}

function getShareable(txt, funcResults) {
    url = '/manager/ajax/get-shareable/';
    csfr = $("{% csrf_token %}").val();
    object = {
        'to_share': txt,
        'csrfmiddlewaretoken': csfr,
    };
    $.post(url, object).done(funcResults);
}

function voltpy_loading_start(text) {
    $('body').css('overflow','hidden');
    cover = $('<div id="COVER" class="loading_cover">' + text + '</div>');
    $('body').append(cover);
    $('#COVER').css('line-height', $('#COVER').css('height'));
};

function voltpy_loading_done()
{
    cover = $('#COVER');
    cover.remove();
};

// Function used for communication between the page and server, with loading text.
function voltpy_query(url, object, funcOnReturn) {
    object['csrfmiddlewaretoken'] = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    voltpy_loading_start('Loading ...');
    sleep(10);
    function retFun(data) {
        funcOnReturn(data);
        voltpy_loading_done();
    }
    $.post(url, object).done(retFun);
};

function queryServer(url, object, plot=null, lineData=null, cursors=null) {
    function processReplyPartial (data) {
        processJSONReply(data, plot, lineData, cursors);
    }
    voltpy_query(url, object, processReplyPartial);
};

// This is main JS function for sending and processing JSON.
function processJSONReply(data, plot='', lineData='', cursors='') {
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
        $(e.target).parent('div').toggleClass('invisible');
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
    iclassDisable = '_voltJS_ifNegativeDisable@';
    iclassEnable = '_voltJS_ifNegativeEnable@';
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
            $( '.' + classToHide ).addClass('at_hideable');
        }
        if (value != -1 ) {
            var classToShow = '_voltJS_changeValue_' + value;
            $( "." + classToShow ).removeClass('at_hideable');
        }
        window.voltPy1.ChangeDispCurrent = value;
    });
});

$( function() {
    // TODO: find some nicer way to change Bokeh plots colors
    var iclass = '_voltJS_highlightCurve@';
    function highlightOn(element) { // on hover in
        $(element).css('background-color', 'red');
        $(element).css('color', 'white');
        var classes = element.className.split(' ');
        classes.forEach( function(name) {
            if (name.startsWith(iclass)) {
                var number = name.substring(iclass.length);
                var cname = 'curve_' + number;
                Bokeh.documents[0].get_model_by_name(cname).glyph.line_width = 8;
                Bokeh.documents[0].get_model_by_name(cname).glyph.line_color = 'red';
            }
        }); 
    };
{% load colors %}
    function highlightOff(element) { // on hover out
        var classes = element.className.split(' ');
        $(element).css('background-color', '{% color3 %}');
        $(element).css('color', '{% color3font %}');
        classes.forEach( function(name) {
            if (name.startsWith(iclass)) {
                var number = name.substring(iclass.length);
                var cname = 'curve_' + number;
                Bokeh.documents[0].get_model_by_name(cname).glyph.line_width = 2;
                Bokeh.documents[0].get_model_by_name(cname).glyph.line_color = 'blue';
            }
        }); 
    }

    $( '._voltJS_plotHighlight' ).hover(
        function() {
            highlightOn(this);
        }, function() {
            highlightOff(this);
        }
    );
    $( '._voltJS_plotHighlightInput' ).focusin(
        function() { highlightOn(this) }
    );
    $( '._voltJS_plotHighlightInput' ).focusout(
        function() { highlightOff(this); }
    );
});

$( function() {
    $( '._voltJS_toggleShow' ).on('change', function(e) {
        toggleShow(e.target);
    });
});
function toggleShow(e) {
    $(e.target).next('._voltJS_toShow' ).toggleClass('invisible visible');
}

function toggleDetails(src, field_id) {
    clicked = $(src);
    if ($(field_id).hasClass('invisible')) {
        clicked.text(clicked.text().replace('↧', '↥'));
    } else {
        clicked.text(clicked.text().replace('↥', '↧'));
    }
    $(field_id).toggleClass('invisible');
}

$( function() {
    $('._disabled').attr('disabled', 'disabled');
});

$( function() {
    $('._voltJS_requestLink').click( function() {
        to_send = window.location.href;
        getShareable(to_send, displayLinks);
    });
});

function displayLinks(data) {
    var amd = $('#share_link');
    amd.removeClass('invisible');
    var form = '<a class="closeX" onclick="closeShare();"></a><br /><br />';
    form += 'The following urls will allow to acces the data without logging in:';
    form += '<p>Read only: ' + data['link_ro'] + '</p>';
    form += '<p>Editable: ' + data['link_rw'] + '</p>';

    amd.text('');
    amd.append($(form));
    amd.css('width', '50em');
    amd.css('right', '10px');
}

function closeShare() {
    $('#share_link').addClass('invisible');
}

$( function() {
    imodel = '_voltJS_model@';
    $('._voltJS_applyModel').click( function() {
        var classes = this.className.split(' ');
        classes.forEach( function(name) {
            if (name.startsWith(imodel)) {
                var number = name.substring(imodel.length);
                addApplyToDatasetChooser(number);
            }
        });
    });
});

function addApplyToDatasetChooser(model_num) {
    var amd = $('#id_ApplyModel');
    if (amd.length) {
        if (amd.css('display') == 'none') {
            amd.css('display', 'block');
        } else {
            amd.css('display', 'none');
        }
        return;
    }
    form = '<div class="floatMenu" id="id_ApplyModel">';
    form += '<a class="closeX" onclick=""></a>';
    form += 'Search: <input type="text" onkeyup="setCurveList(' + model_num + ', \'curve_list\');" id="curveSearch" /><br />';
    form += 'Apply to:<div id="curve_list"></div></div>';
    $('body').append($(form));
    setCurveList(model_num, 'curve_list');
}

function setCurveList(model_num, id_where) {
    txt = $('#curveSearch').val();
    function setLinks(data) {
        setApplyModelLinks(model_num, id_where, data);
    }
    searchDataset(txt, setLinks);
}

function setApplyModelLinks(model_num, id_where, data) {
    $('#' + id_where).empty();
    kdata = data['result'];
    for (key in kdata) {
        $('#' + id_where).append($('<a href="/manager/apply-model/an/' + model_num + '/' + key + '/">id' + key + ': ' + kdata[key] + '</a> <br />'));
    }
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

function toggleMethod(type) {
    class_name = '.' + type + '_methods';
    $(class_name).toggleClass('invisible');
}

function selectMethod(mtype, mname, mdisp, toggle=true) {
    $('#' + mtype + '_selected').text('Selected: ' + mdisp + " ")
    input = $('<input type="hidden" name="' + mtype + '-method" value="' + mname + '" />');
    if (mtype == 'analysis') {
        but = $('<input type="submit" name="startAnalyze" value="Start Analysis" class="formSubmit" />');
    } else {
        but = $('<input type="submit" name="startProcessing" value="Start Processing" class="formSubmit" />');
    }
    $('#' + mtype + '_selected').append(input);
    $('#' + mtype + '_selected').append(but);
    if (toggle) {
        toggleMethod(mtype);
    }
}