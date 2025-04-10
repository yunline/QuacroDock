"use strict";

var default_icon_svg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">
    <circle cx="25" cy="25" r="25" fill="#0b68aa"/>
    <text 
        x="25"
        y="25"
        text-anchor="middle" 
        dominant-baseline="middle"
        font-size="24"
        fill="#eee"
    >Qd</text>
</svg>
`
var default_icon = `data:image/svg+xml;charset=utf8,${encodeURIComponent(default_icon_svg)}`;
const SVG_NS = "http://www.w3.org/2000/svg";


// equivalent HTML:
/* 
<div title="Tab Name" active="0">
    <div class="highlight_bar"></div>
    <div class="icon">
        <img src=""/>
        <svg class="close_btn" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
            <use href="#close_tab_btn_icon"/>
        </svg>     
    </div>
    <p class="name_label">Tab Name</p>
</div>
*/

class Tab {
    constructor(container, tab_name, icon, tab_id) {
        this.tab_id = tab_id;
        this.container = container;

        this.element = document.createElement("div");
        this.element.setAttribute("active","0");
        this.element.setAttribute("title", tab_name)

        let highlight_bar = document.createElement("div");
        highlight_bar.setAttribute("class","highlight_bar");
        this.element.appendChild(highlight_bar);

        let icon_frame = document.createElement("div");
        icon_frame.setAttribute("class","icon");
        {
            this.icon_image_element = document.createElement("img");
            this.icon_image_element.setAttribute("src", icon);
            icon_frame.appendChild(this.icon_image_element);

            this.close_tab_btn = document.createElementNS(SVG_NS,"svg");
            this.close_tab_btn.setAttribute("class","close_btn");
            this.close_tab_btn.setAttribute("viewBox","0 0 50 50");
            let close_icon = document.createElementNS(SVG_NS, "use");
            close_icon.setAttribute("href","#close_tab_btn_icon");
            this.close_tab_btn.appendChild(close_icon);
            icon_frame.appendChild(this.close_tab_btn);
        }
        this.element.appendChild(icon_frame);

        this.name_label_element = document.createElement("p");
        this.name_label_element.setAttribute("class","name_label");
        this.name_label_element.innerText = tab_name;
        this.element.appendChild(this.name_label_element);

        this.register_events();
    }

    update_icon(icon) {
        this.icon_image_element.setAttribute("src", icon);
    }

    register_events(){
        this.element.onclick = (event) => {
            this.container.request_activate_tab(this.tab_id);
        }
        this.close_tab_btn.onclick = (event) => {
            event.stopPropagation();
            this.container.request_close_tab(this.tab_id);
        }
    }

    activate() {
        this.element.setAttribute("active","1");
    }

    deactivate() {
        this.element.setAttribute("active","0");
    }
}

class TabList{
    constructor(){
        this.element = document.getElementById("tab_list");
        this.tab_id_map = {};
        this.tab_activated = null;
    }    

    create_tab(tab_name, tab_id) {
        // Called by python backend

        if(tab_id in this.tab_id_map) {
            throw TypeError(`Tab id ${tab_id} has been exist`);
        }
        let new_tab = new Tab(this, tab_name, default_icon, tab_id);
        this.element.appendChild(new_tab.element);
        this.tab_id_map[tab_id] = new_tab;
        this.request_get_icon(tab_id);
        return new_tab;
    }

    remove_tab(tab_id){
        // Called by python backend

        let to_be_del_tab = this.tab_id_map[tab_id];
        if (to_be_del_tab===undefined) {
            throw TypeError(`Invalid tab id ${tab_id}`);
        }
        if (to_be_del_tab===this.tab_activated) {
            this.tab_activated=null;
        }
        this.element.removeChild(to_be_del_tab.element);
        delete this.tab_id_map[tab_id];
    }

    activate_tab(tab_id) {
        // Called by python backend
        if(this.tab_activated!==null) {
            this.tab_activated.deactivate();
        }
        this.tab_activated = this.tab_id_map[tab_id];
        this.tab_activated.activate();
    }

    request_get_icon(tab_id) {
        pywebview.api.api_get_icon(tab_id).then(result => {
            if(result) {
                this.tab_id_map[tab_id].update_icon(result);
            }
        })
    }

    request_activate_tab(tab_id) {
        // if the tab was activated, just return
        if(this.tab_activated!==null&&this.tab_activated.tab_id==tab_id){
            return;
        }

        pywebview.api.api_activate_tab(tab_id);
        
    }

    request_close_tab(tab_id) {
        pywebview.api.api_close_tab(tab_id);
    }
}

window.onload = () => {
    function setup_resize_region() {
        var initial_x = 0;
    
        function on_mouse_move(ev) {
            let x = ev.screenX-initial_x;
            pywebview.api.api_horizontal_resize(x);
        }
    
        function on_mouse_up() {
            window.removeEventListener('mousemove', on_mouse_move);
            window.removeEventListener('mouseup', on_mouse_up);
        }
    
        function on_mouse_down(ev) {
            initial_x = ev.clientX;
            window.addEventListener('mouseup', on_mouse_up);
            window.addEventListener('mousemove', on_mouse_move);
        }
    
        var resize_blocks = document.querySelectorAll('#horizontal_resize_region');
        for (var i=0; i < resize_blocks.length; i++) {
            resize_blocks[i].addEventListener('mousedown', on_mouse_down);
        }
    }
    setup_resize_region();
};

