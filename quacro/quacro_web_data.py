# this file is auto generated
frontend_html = '<script>`use strict`;var default_icon_svg=`\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">\n    <circle cx="25" cy="25" r="25" fill="#0b68aa"/>\n    <text \n        x="25"\n        y="25"\n        text-anchor="middle" \n        dominant-baseline="middle"\n        font-size="24"\n        fill="#eee"\n    >Qd</text>\n</svg>\n`;var default_icon=`data:image/svg+xml;charset=utf8,${encodeURIComponent(default_icon_svg)}`;const SVG_NS=`http://www.w3.org/2000/svg`;class Tab{constructor(a,b,c,d){this.tab_id=d;this.container=a;this.element=document.createElement(`div`);this.element.setAttribute(`active`,`0`);this.element.setAttribute(`title`,b);let e=document.createElement(`div`);e.setAttribute(`class`,`highlight_bar`);this.element.appendChild(e);let f=document.createElement(`div`);f.setAttribute(`class`,`icon`);{this.icon_image_element=document.createElement(`img`);this.icon_image_element.setAttribute(`src`,c);f.appendChild(this.icon_image_element);this.close_tab_btn=document.createElementNS(SVG_NS,`svg`);this.close_tab_btn.setAttribute(`class`,`close_btn`);this.close_tab_btn.setAttribute(`viewBox`,`0 0 50 50`);let a=document.createElementNS(SVG_NS,`use`);a.setAttribute(`href`,`#close_tab_btn_icon`);this.close_tab_btn.appendChild(a);f.appendChild(this.close_tab_btn)}this.element.appendChild(f);this.name_label_element=document.createElement(`p`);this.name_label_element.setAttribute(`class`,`name_label`);this.name_label_element.innerText=b;this.element.appendChild(this.name_label_element);this.register_events()}update_icon(a){this.icon_image_element.setAttribute(`src`,a)}update_title(a){this.element.setAttribute(`title`,a);this.name_label_element.innerText=a}register_events(){this.element.onclick=a=>{this.container.request_activate_tab(this.tab_id)};this.close_tab_btn.onclick=a=>{a.stopPropagation();this.container.request_close_tab(this.tab_id)}}activate(){this.element.setAttribute(`active`,`1`)}deactivate(){this.element.setAttribute(`active`,`0`)}}class TabList{constructor(){this.element=document.getElementById(`tab_list`);this.tab_id_map={};this.tab_activated=null}create_tab(a,b){if(b in this.tab_id_map)throw TypeError(`Tab id ${b} has been exist`);let c=new Tab(this,a,default_icon,b);this.element.appendChild(c.element);this.tab_id_map[b]=c;this.request_get_icon(b);return c}remove_tab(a){let b=this.tab_id_map[a];if(b===undefined)throw TypeError(`Invalid tab id ${a}`);b===this.tab_activated&&(this.tab_activated=null);this.element.removeChild(b.element);delete this.tab_id_map[a]}activate_tab(a){this.tab_activated!==null&&this.tab_activated.deactivate();this.tab_activated=this.tab_id_map[a];this.tab_activated.activate()}request_get_icon(a){pywebview.api.api_get_icon(a).then(b=>{b&&this.tab_id_map[a].update_icon(b)})}request_get_title(a){pywebview.api.api_get_title(a).then(b=>{b&&this.tab_id_map[a].update_title(b)})}request_activate_tab(a){if(this.tab_activated!==null&&this.tab_activated.tab_id==a)return undefined;pywebview.api.api_activate_tab(a)}request_close_tab(a){pywebview.api.api_close_tab(a)}}window.onload=()=>{var a=(()=>{var c=(()=>{window.removeEventListener(`mousemove`,b);window.removeEventListener(`mouseup`,c)});var d=(d=>{a=d.clientX;window.addEventListener(`mouseup`,c);window.addEventListener(`mousemove`,b)});var b=(b=>{let c=b.screenX- a;pywebview.api.api_horizontal_resize(c)});var a=0;var e=document.querySelectorAll(`#horizontal_resize_region`);for(var f=0;f<e.length;f++)e[f].addEventListener(`mousedown`,d)});a()}</script><style>body{user-select:none;background-color:#f4f4f4;flex-direction:column;width:100%;height:100%;margin:0;padding:0;display:flex;overflow:hidden}#horizontal_resize_region{opacity:0;width:5px;margin:0;position:fixed;top:0;bottom:0;left:0}#horizontal_resize_region:hover{cursor:ew-resize}#top_bar{z-index:1;-webkit-app-region:drag;background-image:linear-gradient(30deg,#09f,#5eabef);height:50px;box-shadow:0 1px 4px #999}#top_bar>p{color:#fff;margin:10px 10px 10px 15px;font-size:15px}#bottom_bar{z-index:1;background-color:#f0f0f0;height:50px;box-shadow:0 -2px 5px #ccc}#tab_list{scrollbar-width:none;z-index:0;height:100%;margin:0;padding:0;transition:all .25s;overflow:hidden auto}#tab_list:hover{scrollbar-width:thin}#tab_list>div{background-color:#f0f0f0;flex-direction:row;align-items:center;width:100vw;height:64px;margin:0;transition:inherit;display:flex;left:0}#tab_list>div[active="1"]{background-color:#ddd}#tab_list>div:hover{cursor:pointer;background-color:#ccc}#tab_list>div>.icon{aspect-ratio:1;flex-shrink:0;height:70%;margin-left:10px;margin-right:10px;transition:inherit;position:relative}#tab_list>div>.icon>img{filter:drop-shadow(1px 1px 1px #00000050);-webkit-user-drag:none;width:100%;height:100%}#tab_list>div>.icon>.close_btn{filter:grayscale()brightness(2);opacity:0;height:16px;transition:inherit;position:absolute;top:-4px;right:-4px}#tab_list>div:hover>.icon>.close_btn{opacity:.8}#tab_list>div>.icon>.close_btn:hover{filter:none;transform:rotate(90deg)}#tab_list>div>.highlight_bar{opacity:0;background-color:#00aee8;flex-shrink:0;width:5px;height:100%;transition:inherit}#tab_list>div[active="1"]>.highlight_bar{opacity:1}#tab_list>div>.name_label{text-wrap:nowrap;flex-grow:1;overflow:hidden;mask-image:linear-gradient(270deg,#0000,#000 30%)}@media (width>=100px){#tab_list>div>.name_label,#top_bar>p#title_long{display:block}#top_bar>p#title_mini{display:none}}@media (width<=100px){#tab_list>div>.name_label,#top_bar>p#title_long{display:none}#top_bar>p#title_mini{display:block}}</style></head><svg display=none xmlns=http://www.w3.org/2000/svg><g id=close_tab_btn_icon stroke=white stroke-linecap=round stroke-width=4><circle cx=25 cy=25 fill=#e81123 r=25 stroke=none /><line x1=14 x2=36 y1=14 y2=36 /><line x1=36 x2=14 y1=14 y2=36 /></g></svg><body><div id=top_bar><p id=title_long>QuacroDock<p id=title_mini>Quacro</div><div id=tab_list></div><div id=bottom_bar></div><div id=horizontal_resize_region></div>'
