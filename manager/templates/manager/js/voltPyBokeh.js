<script>
function setMainPlotSize() {
  var proportion = 1.2;
  var winHeight = $(window).height();
  var winWidth = $(window).width();
  var w = Math.floor(winWidth/2.1);
  var h = Math.floor(w/proportion);
  /*
  if (h>(winHeight*0.85)) {
    h = Math.floor(winHeight*0.85);
    w = Math.floor(h*proportion);
  }
  */
  $('._voltPy_bokehSize').css('width', w);
  $('._voltPy_bokehSize').css('height', h);
  $('._voltPy_bokehButtonsSize').css('width', w);
  window.dispatchEvent(new Event('resize'))
  
}
$(function(){
  setMainPlotSize();
});
</script>