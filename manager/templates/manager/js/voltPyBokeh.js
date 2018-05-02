<script>
function setMainPlotSize() {
  var proportion = 1.2;
  var winHeight = $(window).height();
  var winWidth = $(window).width();
  var w = Math.floor(winWidth/2.1);
  var h = Math.floor(w/proportion);
  if (h<(winHeight*0.85)) {
    w = Math.floor(h*0.85*proportion);
    h = Math.floor(w/proportion);
  }
  $('._voltPy_bokehSize').css('width', w);
  $('._voltPy_bokehSize').css('height', h);
  $('._voltPy_bokehButtonsSize').css('width', w);
  
}
$(function(){
  setMainPlotSize();
});
</script>