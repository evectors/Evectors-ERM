/*
	ERM API Explorer front-end code
	version 1.0.0
	last modified 4/31/11 by MB
	Copyright (c) 2011 Evectors Ltd.
*/

var selector = {																					// API endpoints selector object

	id: 'selector',																					// selector element DOM id

	selected: '',																					// selected endpoint

	init: function () {																				// create onclick handlers
		var container = document.getElementById (this.id);
		var links = container.getElementsByTagName ('a');

		for (var i = 0; i < links.length; i++) {
			links[i].onclick = this.select;
		}
	},																		// create onclick handlers

	select: function (evt) {																		// endpoints menu click handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
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

		var def = document.getElementById (target.id + '_p_default');
		def.checked = true;
	}																	// endpoints menu click handler
};																				// API endpoints selector object

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

		var inputs = $("input[type='text'].def");													// loop thru all text inputs of class def
		var def_val = '';

		for (var i = 0; i < inputs.length; i++) {
			def_val = (inputs[i].className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';
			inputs[i].style.color = '#ddd';
			inputs[i].value = def_val;
			inputs[i].onfocus = this.focus;
			inputs[i].onblur = this.blur;
		}
	},																		// initialize object

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
		var inputs = $("input[type='text'].def");													// loop thru all text inputs of class def
		var def_val = '';

		for (var i = 0; i < inputs.length; i++) {													// clear all sttribute default values
			def_val = (inputs[i].className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';
			inputs[i].value = (inputs[i].value == def_val) ? '' : inputs[i].value;
		}

		request.show ();
		var result = request.execute ();
	},																		// send button click handler

	focus: function (evt) {																			// input field focus handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
		var def_val = (target.className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';

		if (target.value == def_val) {
			target.style.color = 'black';
			target.value = '';
		}
	},																	// input field focus handler

	blur : function (evt) {																			// input field blur handler
		evt = (evt) ? evt : window.event;
		var target = (evt.target) ? evt.target : evt.srcElement;
		var def_val = (target.className.indexOf ('dict') != -1) ? 'enter a json array of objects' : 'enter a json object';

		if (target.value == '') {
			target.style.color = '#ddd';
			target.value = def_val;
		}
	}																		// input field blur handler
};																					// parameters pane object

var request = {																						// api request object

	key: 'aaa',																						// default API key, update with real key on production server.

	data : {},																						// POST/PUT/DELETE request parameters

	show: function () {																				// display request string
		var request_str = '<strong>' + pane.selected.toUpperCase () + '&nbsp;</strong>' + location.protocol + '//' + location.host + '/core/api/[api_key]/' + selector.selected + '/';
		var panel = document.getElementById (selector.selected + '_p_' + pane.selected);
		var inputs = panel.getElementsByTagName ('input');

		if (pane.selected.match (/(get|delete)/)) {													// GET/DELETE request
			var search = '';

			for (var i = 0; i < inputs.length; i++) {
				search += (inputs[i].value) ? ((search) ? ';' : '') + inputs[i].name + '=' + inputs[i].value : '';
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
		var url = '/core/api/' + this.key + '/' + selector.selected + '/';
		var panel = document.getElementById (selector.selected + '_p_' + pane.selected);
		var inputs = panel.getElementsByTagName ('input');

		var search = '';
		if (pane.selected.match (/(get|delete)/)) {

			for (var i = 0; i < inputs.length; i++) {
				search += (inputs[i].value) ? ((search) ? ';' : '') + inputs[i].name + '=' + inputs[i].value : '';
			}
		}
		url += search;
		document.getElementById ('result').innerHTML = '<pre>working...</pre>';

		$.ajax ({
			type: pane.selected.toUpperCase (),
			url: url,
			data: (pane.selected.match (/(get|delete)/)) ? '' : JSON.stringify (request.data),
			dataType: 'json',

			success: function (json) {
				request.display_result (JSON.stringify(json, null, 4));
			},

			error: function (XMLHttpRequest, textStatus, errorThrown) {
				request.display_result (textStatus + ': ' + errorThrown);
			}
		});
	},																		// send request to back-end

	display_result: function (result) {																	// display request result
		document.getElementById ('result').innerHTML = '<pre>' + result + '</pre>';
	}															// display request result
};																				// api request object

var result = {																						// result pane object

	getDimensions: function () {																	// returns window dimensions array
		var x, y;

		if (window.innerHeight) {																		// all except Explorer
			x = window.innerWidth;
			y = window.innerHeight;
		} else if (document.documentElement && document.documentElement.clientHeight) {					// Explorer 6 Strict Mode
			x = document.documentElement.clientWidth;
			y = document.documentElement.clientHeight;
		} else if (document.body) {																		// other Explorers
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
	selector.init ();																				// endpoints selection object
	pane.init ();																					// parameters pane object
	result.init ();																					// result pane object
};																		// global initialisation

window.onload = init;
window.onresize = result.adjust;
