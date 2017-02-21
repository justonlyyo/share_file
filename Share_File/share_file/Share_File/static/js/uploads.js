/**
 * Created by walle on 17-2-14.
 */
$(function () {
    /*插件文档地址http://chaping.github.io/plupload/doc/*/
    var filters = {
        mime_types: [ //只允许上传图片和zip文件
            {title: "Image files", extensions: "jpg,gif,png"},
            {title: "Zip files", extensions: "zip"}
        ],
        max_file_size: '2000000kb', //最大只能上传2g的文件
        prevent_duplicates: true //不允许选取重复文件
    };
    var uploader = new plupload.Uploader({
        browse_button: document.getElementById("browse"),
        url: "/user_upload_simple",
        flash_swf_url: '../static/js/Moxie.swf',
        silverlight_xap_url: '../static/js/Moxie.xap',
        max_retries: 3,  // 最大重试次数
        filters: filters,  // 过滤器
        drop_element: "drag_area"
    });

    uploader.init();

    // 绑定文件添加进队列事件
    uploader.bind('FilesAdded', function (uploader, files) {
        for (var i = 0, l = files.length; i < l; i++) {
            var file_name = files[i].name;
            var html = "<li id='file_" + files[i].id + "'><p class='file-name'>" + file_name + "</p>" +
                "<p class='progress'></p></li>";
            $(html).appendTo("#file_list");
        }
    });

    /* 其他代码 */

    // 启动页面去掉所有的checkbox
     $(".my_checkbox").removeAttr("checked");

    // 绑定文件上传进度事件
    uploader.bind("UploadProgress", function (uploader, file) {
        $("#file_" + file.id).find(".progress").css({"width": file.percent + "%", "background-color": "lightyellow"}).text(file.percent+"%");
    });

    // 上传按钮事件
    $("#upload_btn").click(function () {
        uploader.start();
    });

    // 上传完成的事件
    uploader.bind("FileUploaded", function(uploader, file){
        $("#file_"+file.id).find(".progress").text("100%").css("background-color", "lightgreen");
        var drag = $("#drag_area");
        drag.html(drag.html()+"<br>"+file.name+" 上传完毕.");
    });

    // 对云盘的操作按钮
    $(".process").click(function(){
        var $this = $(this);
        if($this.text() == "全选"){
            $(".my_checkbox").attr("checked", "checked");
        }
        else if($this.text() == "全不选"){
            $(".my_checkbox").removeAttr("checked");
        }
        else if($this.text() == "改名" || $this.text() == "删除"){
            var checkbox = $(".my_checkbox:checked");
            var type = $this.text();
            if(checkbox.length == 0){
                alert("你还没有选择文件或目录");
            }
            else if(checkbox.length > 1){
                alert("一次只能"+ type +"一个文件或目录的名称");
            }
            else{
                if(type == "改名"){
                    var old_name = checkbox.attr("data-name");
                    var name_obj = prompt("请输入新的名字");
                    if(name_obj && name_obj != ""){
                        // 发送请求
                        edit_somthing({"the_type": "rename",
                            "old_name": old_name,
                        "new_name": name_obj})
                    }
                    else{}
                }
                else{
                    // 删除
                    var astr = "你确实要删除此文件?";
                    if(checkbox.attr("data-type") == "dir"){
                        astr = "你确实要删除此文件夹吗?"
                    }
                    var con = confirm(astr);
                    if(con){
                        var file_name = checkbox.attr("data-name");
                        edit_somthing({"file_name": file_name,
                            "the_type": "delete"});
                    }else{}

                }

            }
        }
        else if($this.text() == "下载文件"){
            var checkbox = $(".my_checkbox:checked");
            if(checkbox.length == 0){
                alert("你还没有选择文件或目录");
            }
            else if(checkbox.length > 1){
                alert("一次只能下载一个文件或目录的名称");
            }
            else if(checkbox.attr("data-type") == "dir"){
                alert("文件夹下载功能暂未开放");
            }
            else{
                var file_name = checkbox.attr("data-name");
                download(file_name);  // 下载文件
                $(".my_checkbox").removeAttr("checked");
            }

        }else{}
    });

    // 删除和改名函数
    edit_somthing = function(data_dict){
        // 删除和改名
        var user_name = $("#current_user_name").text();
        var path = $("#current_path").attr("data-val");
        path = path=="/"?"":path.split("/")[-1];
        data_dict['user_name'] = user_name;
        data_dict['path'] = path;
        // 对文件的删除和更改
        $.post("/edit_file", data_dict, function(data){
            var data = JSON.parse(data);
            if(data['message'] == "success"){
                var mes = data_dict['the_type'] == 'rename'? "修改" : "删除";
                alert(mes + "成功");
                location.reload();
            }
            else{
                alert(data['message']);
            }
        });
    };

    // 只有一级目录
    if($("#current_path").attr("data-val") != "/"){
        $("#new_dir").hide(0);
    }

    // 新建目录相关管操作
    $("#new_dir").click(function(){
        var user_name = $("#current_user_name").text();
        var path = $("#current_path").attr("data-val");
        path = path=="/"?"":path.split("/")[-1];
        var name_obj = prompt("请输入新文件夹的名字");
        if(name_obj){
            $.post("/edit_file",{"the_type": "new_dir",
            "user_name": user_name, "path": path, "file_name":
            name_obj} , function(data){
                var data = JSON.parse(data);
                if(data['message'] == "success"){
                    alert("新建成功");
                    location.reload();
                }
                else{
                    alert(data['message']);
                }
            });
        }else{}
    });

    // 下载文件
    download = function(file_name){
        var user_name = $("#current_user_name").text();
        var path = $("#current_path").attr("data-val");
        path = path=="/"?"":path.split("/")[1];

        window.open("/download/"+user_name+"/?path="+path+"&file_name="+file_name);
    };

    //end!
});
