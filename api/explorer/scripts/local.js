/*
	ERM API Explorer front-end code
	version 1.0.3
	last modified 5/6/2011 by MB
	Copyright (c) 2011 Evectors Ltd.
*/

var _prefix = '/core/api';																			// default API url prefix, defined as global

var args = {																						// API explorer arguments

	init: function () {																				// initialize from location object

		if (location.hash) {																		// get parameters are specified
			var couples = location.hash.split ('&');

			for (var i = 0; i < couples.length; i++) {												// loop thru all name/value couples
				var members = couples[i].split ('=');
				this[members[0].replace (/^\#/, '')] = decodeURIComponent (members[1]).toLowerCase ();	// set argument while trimming leading ?
			}
		}
	}																			// initialize from location object

};																					// api explorer arguments

var selector = {																					// API endpoints selector object

	id: 'selector',																					// selector element DOM id

	selected: '',																					// selected endpoint

	init: function () {																				// create onclick handlers
		var container = document.getElementById (this.id);
		var links = container.getElementsByTagName ('a');

		for (var i = 0; i < links.length; i++) {
			links[i].onclick = this.select;
		}

		if (args.method) {																			// method parameter specified in api explorer request
			this.select (null, args.method);														// select method's parameters pane

			if (args.request) {																		// request parameter specified in api explorer request
				pane.update ();																		// update method's parameters pane according to request
			}
		}
	},																		// create onclick handlers

	select: function (evt, method) {																// endpoints menu click handler
		evt = (evt) ? evt : window.event;
		var target = (method) ? document.getElementById (method) : ((evt.target) ? evt.target : evt.srcElement);
		target = (target.tagName.toLowerCase () == 'a') ? target : target.parentNode;
		var container = document.getElementById (selector.id);
		var options = container.getElementsByTagName ('li');

		for (var i = 0; i < options.length; i++) {													// reset all options background
			options[i].style.background = '#fff';
		}

		target.parentNode.style.background = '#ebeff9';												// set selected option background

		var panels = $('.panel');

		for (var i = 0; i < panels.length; i++) {													// hide all option panels
			panels[i].style.display = 'none';
		}

		document.getElementById (target.id + '_p').style.display = 'block';							// show selected option's panel
		selector.selected = target.id;
		pane.select (selector.selected, 'get');

		var def = document.getElementById (target.id + '_r_get');
		def.checked = true;
	}															// endpoints menu click handler

};																				// api endpoints selector object

var pane = {																						// parameters pane object

	selected: '',																					// selected request type: get/post/put/delete

	init: function () {																				// initialize object
		var radios = $("input[name='request']");

		for (var i = 0; i < radios.length; i++) {													// loop thru all radio buttons
			radios[i].onclick = this.toggle;
		}

		var buttons = $("input[type='button']");

		for (var i = 0; i < buttons.length; i++) {													// look through all regular buttons
			buttons[i].onclick = this.exec;
		}

		var mores = $("a.more");

		for (var i = 0; i < mores.length; i++) {													// look through all 'more parameters' links
			mores[i].onclick = this.togglemore;
		}

		var inputs = $("input[type='text'].def");													// loop thru all text inputs of class def
		var def_val = '';

		for (var i = 0; i < inputs.length; i++) {
			def_val = (inputs[i].className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';
			inputs[i].style.color = '#ccc';
			inputs[i].value = def_val;
			inputs[i].onfocus = this.focus;
			inputs[i].onblur = this.blur;
		}

		var areas = $("textarea[name='more']");
		def_val = "parameter=value\n...\nparameter=value";

		for (var i = 0; i < areas.length; i++) {													// look through all 'more parameters' textareas
			areas[i].onfocus = this.focus;
			areas[i].onblur = this.blur;

			if (areas[i].id && areas[i].id.indexOf ('custom') != -1) {								// this is one of the custom method textareas

				if (areas[i].value && areas[i].value != def_val) {									// textarea has some actual content
					areas[i].style.color = 'black';
				} else {																			// textarea is empty
					areas[i].style.color = '#ccc';
					areas[i].value = def_val;														// set default value
				}
			}
		}

		document.onkeyup = this.keyhandler;															// instal form specific key handler
	},																		// initialize object

	keyhandler: function (evt) {
		evt = evt ? evt : window.event;																// equalize event between W3C and IE
		var charCode = (evt.charCode) ? evt.charCode : ((evt.which) ? evt.which : evt.keyCode);
		var target = (evt.target) ? evt.target : evt.srcElement;

		switch (charCode) {

			case 13:																				// return was pressed

				if (target && target.tagName.toLowerCase () == 'input') {							// within a regular text input field
					pane.exec ();																	// 'this' refers to the window when executing
					return false;
				}

				break;

			case 85:
			case 117:																				// 'u' was pressed

				if (evt.shiftKey && (evt.ctrlKey || evt.metaKey)) {									// control + shift
					pane.urlencode (target);														// encodeURIComponent field contents
					return false;
				}

				break;

			default:
				break;

		}

		return true;
	},																// trap enter

	urlencode: function (elem) {																	// encodeURIComponent element's contents

		if (elem && elem.value) {
			var start, stop, text;

			if (elem.setSelectionRange) {															// Gecko + Webkit
				start = elem.selectionStart;
				stop = elem.selectionEnd;
				text = elem.value.substring (start, stop);
			} else if (document.selection) {														// IE
				var range = document.selection.createRange ();
				text = range.text;
				var r1 = range.duplicate ();
				r1.moveToElementText (elem);
				r1.setEndPoint ('EndToEnd', range);
				start=r1.text.length-text.length;
				stop = start + text.length;
			}

			text = (start == stop) ? elem.value : text;												// take whole field value if no selected part

			text = encodeURIComponent (text);
			var before = elem.value.substring (0, start);
			var after = elem.value.substring (stop, elem.value.length);
			elem.value = (start == stop) ? text : before + text + after;							// insert or replace with encoded contents
		}
	},																// encodeURIComponent element's contents

	toggle: function (evt) {																		// request type radio buttons click handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
		pane.select (selector.selected, target.className);
	},																	// request type radio buttons click handler

	select: function (method, request) {															// select parameters pane based on endpoint and request type
		var cmds = $('.cmd');

		for (var i = 0; i < cmds.length; i++) {														// hide all parameter panes
			cmds[i].style.display = 'none';
		}

		var container = document.getElementById (method + '_p_' + request);

		if (container) {
			container.style.display = 'block';
		}

		this.selected = request;
	},														// select parameters pane based on endpoint and request type

	exec: function (evt) {																			// send button click handler
		var def_val = '';
		var inputs = $("input[type='text'].def");													// loop thru all text inputs of class def

		for (var i = 0; i < inputs.length; i++) {													// clear all attribute default values
			def_val = (inputs[i].className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';
			inputs[i].value = (inputs[i].value == def_val) ? '' : inputs[i].value;
		}

		def_val = "parameter=value\n...\nparameter=value";
		var areas = $("textarea[name='more']");

		for (var i = 0; i < areas.length; i++) {													// clear all 'more parameters' default values
			areas[i].value = (areas[i].value == def_val) ? '' : areas[i].value;
		}

		request.show ();
		var result = request.execute ();
	},																		// send button click handler

	focus: function (evt) {																			// input field focus handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
		var def_val = (target.className && target.className != 'custom') ? ((target.className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object') : "parameter=value\n...\nparameter=value";

		if (target.value == def_val) {
			target.style.color = 'black';
			target.value = '';
		}
	},																	// input field focus handler

	blur : function (evt) {																			// input field blur handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
		var def_val = (target.className && target.className != 'custom') ? ((target.className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object') : "parameter=value\n...\nparameter=value";

		if (target.value == '') {
			target.style.color = '#ccc';
			target.value = def_val;
		}
	},																	// input field blur handler

	togglemore: function (evt) {
		var rows = $('#' + selector.selected + '_p_' + pane.selected + ' table tr.nd');				// point to table row hosting the 'more parameters' textarea
		rows[0].style.display = (rows[0].style.display == 'table-row') ? 'none' : 'table-row';		// switch visibiity
		var area = document.getElementById (selector.selected + '_p_' + pane.selected + '_more');	// point to the 'more parameters' textarea
		var def_val = "parameter=value\n...\nparameter=value";

		if (rows[0].style.display == 'table-row') {													// textarea is visible

			if (area.value && area.value != def_val) {												// textarea has some actual content
				area.style.color = 'black';
			} else {
				area.style.color = '#ccc';
				area.value = def_val;
			}
		} else {																					// textarea is hidden
			area.value = (area.value == def_val) ? '' : area.value;									// make sure default value is taken off
		}
	},																// show/hide more parameters

	update: function () {																			// update fields according to explorer request argument
		var radio = document.getElementById (args.method + '_r_' + args.request);

		if (radio) {																				// matching radio button found
			radio.checked = true;
			this.select (selector.selected, args.request);
			var inputs = document.getElementById (args.method + '_p_' + args.request).getElementsByTagName ('input');

			for (arg in args) {																		// loop through all api explorer request parameters

				if (arg != 'init' && arg != 'method' && arg != 'request') {							// filter out 'reserved' parameters

					if (arg == 'custom_method') {													// 'custom_method' parameter found
						document.getElementById (arg).value = args[arg];							// set custom_method value
					} else if (arg == 'more') {														// 'more' parameter
						var area = document.getElementById (args.method + '_p_' + args.request + '_more');
						area.value = args[arg];														// set textarea value
						area.style.color = 'black';
						var rows = $('#' + args.method + '_p_' + args.request + ' table tr.nd');	// point to table row hosting the 'more parameters' textarea

						if (rows[0]) {																// table row exists
							rows[0].style.display = 'table-row';									// make it visible
						}
					} else {																		// all other request parameters should match text input fields

						for (var i = 0; i < inputs.length; i++) {									// loop through all remaining parameters

							if (inputs[i].name == arg) {											// matching input field located
								inputs[i].value = args[arg];										// set input field value
							}
						}
					}
				}
			}
		}
	}																		// update fields according to explorer request argument

};																					// parameters pane object

var request = {																						// api request object

	key: 'aaa',																						// default API key, update with real key on production server.

	data : {},																						// POST/PUT/DELETE request parameters

	show: function () {																				// display request string
		var method = (selector.selected == 'custom') ? document.getElementById ('custom_method').value.replace (/\s+/g, '') : selector.selected;
		var request_str = '<strong>' + pane.selected.toUpperCase () + '&nbsp;</strong>' + location.protocol + '//' + location.host + _prefix + '/[api_key]/' + method + '/';
		var panel = document.getElementById (selector.selected + '_p_' + pane.selected);
		var inputs = panel.getElementsByTagName ('input');
		var area = document.getElementById (selector.selected + '_p_' + pane.selected + '_more');

		if (pane.selected.match (/(get|delete)/)) {													// GET/DELETE request
			var search = '';

			for (var i = 0; i < inputs.length; i++) {
				search += (inputs[i].value) ? ((search) ? ';' : '') + inputs[i].name + '=' + inputs[i].value : '';
			}

			if (area.value) {																		// more parameters were specified
				var lines = area.value.split (/[\r\n;]/);

				for (var i = 0; i < lines.length; i++) {											// loop thru all parameter lines
					var members = lines[i].split ('=');

					if (members[0] && members[1]) {													// both name and value are properly specified
						p = members[1].replace (/^\s+/, '');										// trim leading white spaces
						p = p.replace (/\s+$/, '');													// trim trailing white spaces
						search += ((search) ? ';' : '') + members[0].replace (/\s+/g, '') + '=' + encodeURIComponent (p);
					}
				}
			}

			request_str += search;
		} else {																					// POST/PUT requests
			this.data = {};
			var re = new RegExp ('({|"|,)');														// matches any of the following: { " ,

			for (var i = 0; i < inputs.length; i++) {

				if (inputs[i].value) {																// field is not empty
					var p = inputs[i].value;														// save field value as string

					if (inputs[i].value.match (re)) {												// field value looks like json

						try {																		// try parsing json string into object
							p = JSON.parse (inputs[i].value);
						} catch (e) {																// advise and abort on error
							alert ('Invalid JSON encoding for ' + inputs[i].name);
							this.data = {};
							return;
						}
					}

					this.data[inputs[i].name] = p;													// update data object with parsed field value
				}
			}

			if (area.value) {																		// more parameters were specified
				var lines = area.value.split (/[\r\n;]/);

				for (var i = 0; i < lines.length; i++) {											// loop thru all parameter lines
					var members = lines[i].split ('=');

					if (members[0] && members[1]) {													// both name and value are properly specified
						var p = members[1];

						if (members[1].match (re)) {												// parameter value looks like json

							try {																	// try parsing json string into object
								p = JSON.parse (members[1]);
							} catch (e) {															// advise and abort on error
								alert ('Invalid JSON encoding for ' + members[0]);
								this.data = {};
								return;
							}
						} else {																	// value is not json
							p = p.replace (/^\s+/, '');												// trim leading white spaces
							p = p.replace (/\s+$/, '');												// trim trailing white spaces
						}

						this.data[members[0].replace (/\s+/g, '')] = p;
					}
				}
			}

			request_str += '<a href="#" onclick="request.show_params ();return false" title="show request body">show parameters</a>';
		}

		document.getElementById ('query').innerHTML = request_str;
	},																		// display request string

	show_params: function () {																		// show request parameters box
		document.getElementById ('data').innerHTML = 'request body:<pre>' + JSON.stringify(this.data, null, 4) + '</pre><div><a href="#" onclick="request.hide_params ();return false" title="hide request body">close</a></div>';
		document.getElementById ('data').style.display = 'block';
	},																	// show request parameters box

	hide_params: function () {																		// hide request parameters box
		document.getElementById ('data').style.display = 'none';
	},																	// hide request parameters box

	execute: function () {																			// send request to back-end
		var method = (selector.selected == 'custom') ? document.getElementById ('custom_method').value.replace (/\s+/g, '') : selector.selected;
		var url = _prefix + '/' + this.key + '/' + method + '/';									// form request url up to method
		var panel = document.getElementById (selector.selected + '_p_' + pane.selected);
		var inputs = panel.getElementsByTagName ('input');
		var area = document.getElementById (selector.selected + '_p_' + pane.selected + '_more');

		var search = '';

		if (pane.selected.match (/(get|delete)/)) {

			for (var i = 0; i < inputs.length; i++) {
				search += (inputs[i].value) ? ((search) ? ';' : '') + inputs[i].name + '=' + inputs[i].value : '';
			}

			if (area.value) {																		// more parameters were specified
				var lines = area.value.split (/[\r\n;]/);

				for (var i = 0; i < lines.length; i++) {											// loop thru all parameter lines
					var members = lines[i].split ('=');

					if (members[0] && members[1]) {													// both name and value are properly specified
						p = members[1].replace (/^\s+/, '');										// trim leading white spaces
						p = p.replace (/\s+$/, '');													// trim trailing white spaces
						search += ((search) ? ';' : '') + members[0].replace (/\s+/g, '') + '=' + p;
					}
				}
			}
		}

		url += search;																				// add parameters to request url if applicable
		document.getElementById ('result').innerHTML = '<pre>working...</pre>';

		$.ajax ({																					// send actual request via jQuery
			type: pane.selected.toUpperCase (),
			url: url,
			data: (pane.selected.match (/(get|delete)/)) ? '' : JSON.stringify (request.data),
			dataType: 'json',

			success: function (json) {
				request.display_result (JSON.stringify(json, null, 4));
				request.update_location ();
			},

			error: function (XMLHttpRequest, textStatus, errorThrown) {
				request.display_result (textStatus + ': ' + errorThrown);
			}
		});
	},																		// send request to back-end

	display_result: function (result) {																// display request result
		document.getElementById ('result').innerHTML = '<pre>' + result + '</pre>';
	},														// display request result

	update_location: function () {
		var panel = document.getElementById (selector.selected + '_p_' + pane.selected);
		var inputs = panel.getElementsByTagName ('input');
		var method = document.getElementById ('method');
		var area = document.getElementById (selector.selected + '_p_' + pane.selected + '_more');
		var params = '#method=' + selector.selected + '&request=' + pane.selected;

		for (var i = 0; i < inputs.length; i++) {
			params += (inputs[i].value) ? '&' + inputs[i].name + '=' + encodeURIComponent (inputs[i].value) : '';
		}

		params += (selector.selected == 'custom') ? '&custom_method=' + document.getElementById ('custom_method').value.replace (/\s+/g, '') : '';

		if (area.value) {																			// more parameters were specified
			params += '&more=' + encodeURIComponent (area.value);
		}

		window.location.hash = params;
	}

};																				// api request object

var result = {																						// result pane object

	getDimensions: function () {																	// returns window dimensions array
		var x, y;

		if (window.innerHeight) {																	// all except Explorer
			x = window.innerWidth;
			y = window.innerHeight;
		} else if (document.documentElement && document.documentElement.clientHeight) {				// Explorer 6 Strict Mode
			x = document.documentElement.clientWidth;
			y = document.documentElement.clientHeight;
		} else if (document.body) {																	// other Explorers
			x = document.body.clientWidth;
			y = document.body.clientHeight;
		}

		return [x, y];
	},																// returns window dimensions array

	findPos: function (elem) {																		// returns element's position array
		var curleft = curtop = 0;

		if (elem.offsetParent) {

			do {
				curleft += elem.offsetLeft;
				curtop += elem.offsetTop;
			} while (elem = elem.offsetParent);

			return [curleft, curtop];
		}
	},																	// returns element's position array

	adjust: function () {																			// adjust result pane's height
		var d = result.getDimensions ();
		var rslt = document.getElementById ('result');
		var p = result.findPos (rslt);
		var h = d[1] - (p[1] + 50);
		rslt.style.height = h + 'px';
	},																		// adjust result pane's height

	init: function () {																				// initialize object
		this.adjust ();
	}																			// initialize object

};																					// result pane object

var init = function () {																			// global initialisation
	args.init ();																					// explorer parameters object
	selector.init ();																				// endpoints selection object
	pane.init ();																					// parameters pane object
	result.init ();																					// result pane object
};																		// global initialisation

window.onload = init;
window.onresize = result.adjust;
