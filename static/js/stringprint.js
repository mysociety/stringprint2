var hide_state = true;
var page_loaded = false;
var current_section = "";
$(".noscript-anchor").remove()

if (!String.prototype.startsWith) {
  String.prototype.startsWith = function(searchString, position) {
    position = position || 0;
    return this.indexOf(searchString, position) === position;
  };
}

function send_ga(action,value){
	label = $("meta[name=slug]").attr("content")
	value = typeof value !== 'undefined' ? value : null;
	if (typeof ga === 'function') {
		ga('send', 'event', 'StringPrint', action, label, value)
	}
}
    
// opens or closes all notes
$('#master_expand').on('click touchend',function(event){
    event.preventDefault();
    $(".extended-row").toggle();
    $(".extended").fadeToggle();
    hide_state = !hide_state;
    if (hide_state == true) {
        $('#master_expand_link').text("Show All Notes");
        $(".expand-link").slideDown();
    } else {
        $('#master_expand_link').text("Hide All Notes");
        $(".expand-link").slideUp();
    };
});

function changeSelected(id,title,nohash){
    //rename mobile title with section
    if (title.length > 0) {
        $("#mobile-title").text(title);
    } else {
        title = $("meta[name=short_title]").attr("content");
        $("#mobile-title").text(title);
    }
    current_section = title;
	
        font_size = 14
		$("#mobile-title").css("font-size", font_size + "pt");
        while (($("#mobile-navbar-header").height() > ($("#mobile-title").height() * 3)) ){
        font_size = font_size - 2
        $("#mobile-title").css("font-size", font_size + "pt");
        }
        
    if (nohash == undefined){
        nohash = false;
    }
   
    $("li").removeClass("active");
    $("#menu-" + id).addClass("active");
    $("#caret-menu-" + id).addClass("active");
    if (nohash == false){
        harmlessHashChange($("#" + id + ".anchor").attr('name'));
    }
    adjustMenus(id);
	paragraph_id = $("#" + id + ".linkable").attr("first_graf");
	set_mobile_link(paragraph_id);

}


$("a.nav-link").on("click", function(){
    // force refresh of title stuff when link clicked - if we don't cleanly pass a navpoint
	send_ga("Mobile Menu Click",$(this).attr('href'));
	
})

$("a.search_link").on("click", function(){
	send_ga("Search");
})


$("a.alt_link").on("click", function(){
	send_ga("Alt Format - " + $(this).attr('type'));
})


$("a.top-nav-item").on("mouseup", function(){
    // force refresh of title stuff when link clicked - if we don't cleanly pass a navpoint
	send_ga("Top Nav Click",$(this).attr('href'));
    id = $(this).attr('section');
    title = $("#"+id +".section-anchor").text()
    changeSelected(id,title,true);
	
})

var waypoints = $('.section-anchor').waypoint(function(direction) {
    //at change in section changes top menu and hash changes
    if ($(this.element).is(':visible') == false){
    return 0;
    }
    
    if (direction == "down") {
        id = $(this.element).attr('id');
        title = $(this.element).text()
    } else {
        id = $(this.element).attr('prev');
        title = $("#"+id+".section-anchor").text()
    };
	if (page_loaded){
    changeSelected(id,title);
	}

}, {
  // offset very slightly the location of the section anchor
  offset: function() {
    if ($(this.element).is(':visible') == true){
        return $(this.element).height() + 60;
    } else {
    return 0
    }
  },
  
  continuous:false}
  
);


function scrollToView(element){
    var offset = element.offset().top + 20;
    if(!element.is(":visible")) {
        element.css({"visibility":"hidden"}).show();
        var offset = element.offset().top;
        element.css({"visibility":"", "display":""});
    }

    var visible_area_start = $(window).scrollTop();
    var visible_area_end = visible_area_start + window.innerHeight;

    if(offset < visible_area_start || offset > visible_area_end){
         // Not in view so scroll to it
         $('html,body').animate({scrollTop: offset - window.innerHeight/3}, 1000);
         return false;
    }
    return true;
}

//shows an individual footnote
$('.expand-footnotes').on('click touchend',function(event){
    event.preventDefault();
    id = $(this).attr('id');
    name = $(this).attr('name');
    footnotes_window = $("#" + id + ".footnotes")
    footnotes_window.animate({ height: 'toggle', opacity: 'toggle' }, 'slow');
    window.setTimeout(Waypoint.refreshAll,500);
    if (footnotes_window.is(':visible')) {
    scrollToView($("p#" + name));
    }
	send_ga("Show Footnote", id)
 });
 
//hides an individual footnote
 $('.hide-footnotes').on('click touchend',function(event){
    event.preventDefault();
    id = $(this).parent().parent().attr('id');
    $("#" + id + ".footnotes").animate({ height: 'toggle', opacity: 'toggle' }, 'slow');
    window.setTimeout(Waypoint.refreshAll,500);
 });

//shows an individual note
$('.expand-link').on('click touchend',function(event){
    event.preventDefault();
    $(this).fadeOut();
    id = $(this).attr('id');
    $("#" + id + ".extended-row").show();
    $("#" + id + ".extended").animate({ height: 'toggle', opacity: 'toggle' }, 'slow');
    window.setTimeout(Waypoint.refreshAll,500);
	send_ga("Show Note", id)
 });
 
//hides an individual note
 $('.hide-link').on('click touchend',function(event){
    event.preventDefault();
    id = $(this).attr('id');
    $("#" + id + ".extended-row").hide();
    $("#" + id + ".extended").animate({ height: 'toggle', opacity: 'toggle' }, 'slow');
    $("#" + id + ".expand-link").fadeIn();
    window.setTimeout(Waypoint.refreshAll,500);
 });
 
//show citation link as hovering over text
 $( ".content-row" ).on('mouseenter',
  function() {
    id = $(this).attr('id')
    $(".cite-link" ).not(".manual_paragraph").hide();
    $('#' + id + ".cite-link" ).show();
	set_mobile_link(id);
  })

var last_id = 1
var default_past = 1

function set_mobile_link(id){
	//adjust where the top mobile link points
	//break 
var ua = window.navigator.userAgent;
var isIE = /MSIE|Trident/.test(ua);
if ( !isIE ) {

	console.log(id);
	item = $("#" + id + ".cite-link");
	link_ref = item.attr("href");
	para_tag = item.attr("para_tag");
	mobile_link = $(".mobile-header-link");
	mobile_link.attr("href", link_ref);
	mobile_link.attr("para_tag", para_tag);
	mobile_link.prop("id",id);
	}
}


function adjustMenus(id,future, past) {
//adjust what is visible in menus to just the nearby scope
    if (future === undefined) { future = 6; }
    if (future < 0) { future = 0}

    if (past === undefined) { past = default_past; }
    if (past < 0) { past = 0}
    //if this is being called blind (usually resize - go with last known id)
    if (id === undefined) {
        id = last_id
    } else {
        id = parseInt(id)
        last_id = id
        }
	
    last_id = id
    bottombar = id - past
    topbar = id + future
    //unhide correct items
    for(var i=bottombar, len=topbar+1; i < len; i++){
        $("#menu-"+i).removeClass("hide-item");
        $("#caret-menu-"+i).removeClass("hide-item");
    }
    
    //hide incorrect items
    $(".top-menu-item:visible").each(function (){
    
        local = parseInt($(this).attr('item'))
        if (local == 0) {
            local = 1
            future = future + 1
        }
		// console.log(local)
            if ((local <= bottombar) || (local > topbar)) {
                $(this).addClass("hide-item")
            }
        
    
    })
    
    $(".dropdown:visible").each(function (){
    
        local = parseInt($(this).attr('item'))
        if (local == 0) {
            local = 1
            future = future + 1
        }
            if ((local <= bottombar) || (local > topbar)) {
                $(this).addClass("hide-item")
            }
        
    
    })

    
    // set the << button to the previous section
    if (id > 1 && bottombar -1 > 0) {
        prev_link = $('[section='+ bottombar +']').attr('href')
        $("a#menu-prev").show().attr("href",prev_link);
    } else {
        $("a#menu-prev").hide();
    }
    
    next_link = $('[section='+ (bottombar + 2) +']')
    
    if (next_link.length > 0) {
        $("a#menu-next").show().attr("href",next_link.attr('href'));
    } else {
        $("a#menu-next").hide()
    }
    
    //if we're now on two lines - adjust downwards
    if (($("#large-menu").height() > ($("#brand").height() * 3)) ){
        if (past > 1 ){
            adjustMenus(id,future,past-1)
        } else if (future > 0) {
            adjustMenus(id,future-1,past)
        }
    } else {

    }
    
}


function closeCatchup(){  
        $("#catchup").fadeOut()
        return false
}

function harmlessHashChange(newhash){
//changes the hash in the address bar without moving the page
    
    var isiPad = navigator.userAgent.match(/iPad/i) != null;

    if (currently_moving == false && isiPad == false) {

        $("a[name=temp]").each(function() {
            old = $(this).attr("temp_name")
            $(this).attr('name',old)
        })
        
        if (newhash != "temp" ) {
            if (typeof newhash == "undefined") {
                window.location.hash = "start";
            } else {
                existing = $('a[name="' + newhash + '"]')
                existing.attr('temp_name',newhash);
                existing.attr('name',"temp");
                history.replaceState(undefined, undefined, "#" + newhash)
                //window.location.hash = newhash;
                window.setTimeout(function() {existing.attr('name',newhash)},1);

            }
        }
    
    }
}

//extract the catchup information
function assembleCatchup(section_id,current_sub) {

    start = '<div class="row" id="catchup"><div class="col-md-offset-2 col-md-8"><div class="extended" id="catchup"><p><b>Catch Up </b>(<a href="" onclick="return closeCatchup()">close</a>):</p><ul>'
    end = '</ul></div></div></div>'
    body = start
    count = 0
    int_section = parseInt(section_id)
    int_current = parseInt(current_sub)
    //get sections catchup
      for (i = 1; i <= int_section; i++) {
        catch_up = sections[i]['catch_up']
        if (catch_up != ""){
            link = $("#" + i + ".linkable")

            body += '<li>' + catch_up + ' (<a href="#' + link.attr('name') + '">link</a>)</li>' 
            count += 1
        }
      } 

      current_section = sections[int_section]['sub']
      
      for (var key in current_section) {
          if (parseInt(key) < int_current){
            link = $("#" + int_section + "g" + key + ".linkable")
            body += '<li>' + current_section[key] + ' (<a href="#' + link.attr('name') + '">link</a>)</li>'
            count += 1
          }
      }
      body += end
      
      if (count > 0){
        return body
        } else {
        return ""
        }
};
    




var currently_moving = false

function gotoTarget(target,addText,internalMove){

    if (internalMove == undefined) {
        internalMove = false;
    }
    
    if (internalMove == true){
        highlightTime = 5000;
        createCatchup = false;
    } else {
        highlightTime = 20000;
        createCatchup = true;
    }
      
    //clever hash link that adds markers around the right place
    para_id = target.attr('name')
	
            if (addText && currently_moving == false) {
            currently_moving = true
            
            $('#' + para_id + ".extended-row" ).show();
            $('#' + para_id + ".extended" ).show();
            $('#' + para_id + ".catchup-link" ).show();
            $('#' + para_id + ".cite-link" ).addClass("manual_paragraph");
            }
            if (internalMove == false) {
                catchup = assembleCatchup(target.attr("parent"),target.attr('last_title'))
                $("#" + (parseInt(para_id) + 2) + ".content-row").before(catchup)
                $("#catchup.extended").show()
            }
            $('html,body').scrollTop(target.offset().top - 60) //offsets for fixed header
            parent = $("#" + target.attr('parent') + ".anchor")
            $("#" + para_id + ".content-row").removeClass('content-row').addClass("highlighted-content content-row")
            window.setTimeout(function() {$("#" + para_id + ".content-row").removeClass("highlighted-content")},highlightTime)
            currently_moving = false;
			set_mobile_link(para_id);
			if (page_loaded == false){
				id = target.attr('parent')
				title = $("#"+id +".section-anchor").text()
				changeSelected(id,title,true);
			}
}

function gotoHash(hash,addText){
//decodes the clever hash function

	  send_ga("External Section Link", hash)

      key_areas = hash.split(".") //0 - section, 1 paragraph, 2 - prime, 3 - start, 4-end
      if (key_areas[0][0] == "#"){
        key_areas[0] = key_areas[0].substring(1) //remove hash
      }
      internalMove = false
      if (key_areas[0] == "tag") {
        tag = '[tag=' + key_areas[1] +']'
        options = [tag]
        internalMove = true
        addText = ""
      } else {

          key_target = '[key=' + key_areas[2] +']'
          start_end = '[start_key=' + key_areas[3] +']' + '[end_key=' + key_areas[4] +']'
          start_para ='[start_key=' + key_areas[3] +']' + '[position_key=' + key_areas[1] +']'
          end_para = '[end_key=' + key_areas[4] +']' + '[position_key=' + key_areas[1] +']'
          start ='[start_key=' + key_areas[3] +']'
          end = '[end_key=' + key_areas[4] +']'
          para = '[position_key=' + key_areas[1] +']' + '[parent=' + key_areas[0] +']'
          section = '[section=' + key_areas[0] +']'
          
          if (key_areas.length == 5) {
          
          //old style links without the extra letter key
            options = [key_target,start_end,start_para,end_para,start,end,para,section]
          
          } else if (key_areas.length == 6)  {
              //old style links without the extra letter key based on first letters in sentence
              letter_key = '[letter_key=' + key_areas[5] +']'
              options = [key_target,letter_key,start_end,start_para,end_para,start,end,para,section]

          }

          
      }
      
      for(var i=0, len=options.length; i < len; i++){
          target = $(options[i]);
          if (target.length == 1) {
          
            gotoTarget(target,addText,internalMove);
            break;
          }
      }
     
}

//grab local # links
  $('a[href*="#"]:not([href="#"])').on('click touchend',function() {
    if (dragging == false
	    && location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'') 
		&& location.hostname == this.hostname
	    && location.pathname == this.pathname
		&& $(this).hasClass('cite-copy') == false) {
        var splits = this.hash.split(".")

        if (splits[0].startsWith("#ref")) {
        // deals with reference links from the end of the doc
            target = $('[name='+splits[0].slice(1)+']')
            para_id = target.attr('id')
            $('html,body').scrollTop($("#" + para_id).offset().top - 130)
            $("#" + para_id + ".content-row").removeClass('content-row').addClass("highlighted-content content-row")
            window.setTimeout(function() {$("#" + para_id + ".content-row").removeClass("highlighted-content")},2000)
            $("#" + para_id + ".footnotes").show()
            window.setTimeout(Waypoint.refreshAll,500);
            return false;
        
        } else if (splits.length > 1) {
        //deals with complex hash format
            return gotoHash(this.hash.slice(1),false);

        } else {
        // deals with single hash - either section heads or paragraphs
            new_hash = this.hash.slice(1)
            if (new_hash == "index") {
				send_ga("TOC View")
            if ($("div#index").is(':visible') == false) {
                $("div#index").show()
                Waypoint.refreshAll()
            }
            } else {
				index = $("div#index");
                if ((index.is(':visible') == true) && (index.hasClass("hide-index") == true)) {
					
                    $("div#index").hide()
                    Waypoint.refreshAll()
                }
            }
            $('html,body').scrollTop($('a[name="' + new_hash + '"]').offset().top - 60)
            return false
            }
      
      
    } else {

    }
  });
  
var month = new Array();
month[0] = "Jan";
month[1] = "Feb";
month[2] = "Mar";
month[3] = "Apr";
month[4] = "May";
month[5] = "Jun";
month[6] = "Jul";
month[7] = "Aug";
month[8] = "Sept";
month[9] = "Oct";
month[10] = "Nov";
month[11] = "Dec";
  
function getNow(){
	var currentDate = new Date()
	var day = currentDate.getDate()
	var mon = currentDate.getMonth() + 1
	var year = currentDate.getFullYear()
	return day + " " + month[mon-1] + ". " + year
}
  
function citeBox(dialog_title,link, para_id, para_tag){
    //generates pretty citation box
    title = $("meta[name=short_title]").attr("content")
    full_title = $("meta[name=full_title]").attr("content")
    cite_author = $("meta[name=cite_author]").attr("content")
    year = $("meta[name=year]").attr("content")
	org =  $("meta[name=org]").attr("content")
	include_citation =  $("meta[name=include_citation]").attr("content")
	current_section_name = current_section
	if (current_section_name == title) {
		current_section_name = "";
	}
	if (current_section_name) {
		current_section_name = ": " + current_section_name;
		current_section_name = current_section_name.trim();
	}
	
    if (para_tag != "") {
        ele_name = "Paragraph";
        ele_id = para_tag;
    } else {
        ele_name = "Paragraph";
        ele_id = para_id    ;
    };
	
	box_content = 'Link : <a href="' + link+ '">' + title + current_section_name + ', ' + ele_name + ' '+ ele_id + '</a>'
	if (include_citation == "true"){
    box_content = box_content + '<br><br>Cite As:<br><span class="cite"> ' + cite_author + ' (' + year + '), <i>'+ full_title + '</i>. [online] , ' + org + '. '+ ele_name + ': ' + ele_id + ', Available at: '+ link + ' [Accessed ' + getNow() + ']</span>'
	};
    box_content = "<h4><b>" + dialog_title + "</b></h4>" + box_content
    Swal.fire({
    icon: 'success',
    html: box_content,
    confirmButtonText: "OK" });
	
	send_ga("Generated Link", link)
	
}

 //copies link to clipboard - disables further activity
$(".cite-copy").on('click touchend',function(e) {

	link =  $(this).attr("href")
    
	para_id =  $(this).attr("id")
	
    para_tag = $(this).attr("para_tag")
	
	
    
    clipboard.copy(link).then(
      function(){citeBox("Link added to Clipboard!",link,para_id,para_tag);},
      function(err){citeBox("Copy Link From Below!",link,para_id,para_tag);})
  

    e.stopPropagation();
    return false;
});
 
 $("a.caret-link").on('click touchend',function() {
   parent_id = $(this).attr("parent")
   $("#"+ parent_id + ".dropdown-toggle").dropdown("toggle");
   window.location.href = this.href;
   return false
});
  
var dragging = false;

$(".nav-link").on("touchmove", function(){
      dragging = true;
});

$("a").on("touchmove", function(){
      dragging = true;
});
  
$("body").on("touchstart", function(){
    dragging = false;
});
  
$('.nav-link').on('click touchend',
    function () {
	    if (dragging) {
		   return;
		}
        window.location.href = this.href;
        $('.navbar-collapse').removeClass('in');
        return false
    }
);

function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}

$(window).on("load", function () {
    hide_state = $("meta[name=hide_state]").attr("content")
    if (hide_state == "true"){
        hide_state = true
    } else if (hide_state == "false") {
        hide_state = false
    }
       
    if (hide_state == true) {
        $(".extended").hide();
        $(".extended-row").hide();
        $('#master_expand_link').text("Show All Notes");
    } else {
        $('#master_expand_link').text("Hide All Notes");
        $(".expand-link").hide();
    };
	
	if (typeof drawCharts === 'function') {
	drawCharts()
	}

      //Executed on page load with URL containing an anchor tag.
      if(window.location.hash) {
          var hash = window.location.hash;
          splits = hash.split(".");
          if (splits.length > 1) {
		  page_loaded = true;
          return gotoHash(hash,true);
          } else {
              if (hash != "#start") {
                hash = hash.replace("#","")
                section = $('.anchor[name ="' + hash + '"]').first()
                id = section.attr("id");
                title = $("#"+id +".section-anchor").text()
                changeSelected(id,title,true); 
              }
          }
          }
	page_loaded = true;
    

    });
	
function followHash() {
	//allows hash moves within a document
	var splits = location.hash.split(".")
	if (splits.length > 1) {
		gotoHash(location.hash);
		}
}

function window_resize() {
    //fix waypoints on window resize
    adjustMenus();
    Waypoint.refreshAll()
}

window.onresize = window_resize;
window.onhashchange = followHash;
window_resize()
set_mobile_link(1)




