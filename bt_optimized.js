/**
 * 宝塔面板优化脚本
 * 去除各种计算题与延时等待
 * 适用宝塔面板版本：7.7+
 * 优化版本 - 改进性能和代码结构
 */

(function() {
    'use strict';
    
    // 配置对象
    const CONFIG = {
        VERSION: '2.0.0',
        DEBUG: false,
        DELAY_TIMEOUT: 100,
        MAX_RETRIES: 3
    };
    
    // 工具函数
    const Utils = {
        // 安全的对象属性检查
        safeGet: function(obj, path, defaultValue = null) {
            return path.split('.').reduce((current, key) => {
                return current && current[key] !== undefined ? current[key] : defaultValue;
            }, obj);
        },
        
        // 防抖函数
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // 日志函数
        log: function(message, level = 'info') {
            if (CONFIG.DEBUG) {
                console.log(`[BT Optimized] ${level.toUpperCase()}: ${message}`);
            }
        },
        
        // 错误处理
        handleError: function(error, context) {
            Utils.log(`Error in ${context}: ${error.message}`, 'error');
            if (CONFIG.DEBUG) {
                console.error(error);
            }
        }
    };
    
    // 核心优化类
    class BTOptimizer {
        constructor() {
            this.initialized = false;
            this.overrides = new Map();
            this.init();
        }
        
        init() {
            try {
                this.setupConfirmOverrides();
                this.setupPromptOverrides();
                this.setupDatabaseOverrides();
                this.setupSiteOverrides();
                this.setupSafeMessageOverride();
                this.setupDelayRemoval();
                this.initialized = true;
                Utils.log('BT Optimizer initialized successfully');
            } catch (error) {
                Utils.handleError(error, 'BTOptimizer.init');
            }
        }
        
        // 设置确认对话框覆盖
        setupConfirmOverrides() {
            if (typeof bt !== 'undefined' && bt.hasOwnProperty('show_confirm')) {
                this.overrides.set('bt.show_confirm', bt.show_confirm);
                
                bt.show_confirm = function(title, msg, callback, error) {
                    Utils.log('Intercepted show_confirm call');
                    
                    // 立即执行回调，跳过确认
                    if (callback && typeof callback === 'function') {
                        setTimeout(() => {
                            try {
                                callback();
                            } catch (e) {
                                Utils.handleError(e, 'show_confirm callback');
                            }
                        }, CONFIG.DELAY_TIMEOUT);
                    }
                    
                    // 可选：显示简化的确认对话框
                    if (CONFIG.DEBUG) {
                        layer.open({
                            type: 1,
                            title: title,
                            area: "365px",
                            closeBtn: 2,
                            shadeClose: true,
                            btn: [lan?.public?.ok || '确定', lan?.public?.cancel || '取消'],
                            content: `<div class='bt-form webDelete pd20'>
                                <p style='font-size:13px;word-break: break-all;margin-bottom: 5px;'>${msg}</p>
                                ${error || ''}
                            </div>`,
                            yes: function(index, layero) {
                                layer.close(index);
                                if (callback) callback();
                            }
                        });
                    }
                };
            }
        }
        
        // 设置提示确认覆盖
        setupPromptOverrides() {
            if (typeof bt !== 'undefined' && bt.hasOwnProperty('prompt_confirm')) {
                this.overrides.set('bt.prompt_confirm', bt.prompt_confirm);
                
                bt.prompt_confirm = function(title, msg, callback) {
                    Utils.log('Intercepted prompt_confirm call');
                    
                    // 立即执行回调
                    if (callback && typeof callback === 'function') {
                        setTimeout(() => {
                            try {
                                callback();
                            } catch (e) {
                                Utils.handleError(e, 'prompt_confirm callback');
                            }
                        }, CONFIG.DELAY_TIMEOUT);
                    }
                    
                    // 可选：显示简化的提示对话框
                    if (CONFIG.DEBUG) {
                        layer.open({
                            type: 1,
                            title: title,
                            area: "350px",
                            closeBtn: 2,
                            btn: ['确认', '取消'],
                            content: `<div class='bt-form promptDelete pd20'>
                                <p>${msg}</p>
                            </div>`,
                            yes: function(layers, index) {
                                layer.close(layers);
                                if (callback) callback();
                            }
                        });
                    }
                };
            }
        }
        
        // 设置数据库操作覆盖
        setupDatabaseOverrides() {
            if (typeof database !== 'undefined' && database.hasOwnProperty('del_database')) {
                this.overrides.set('database.del_database', database.del_database);
                
                database.del_database = function(wid, dbname, callback) {
                    Utils.log('Intercepted database.del_database call');
                    
                    const title = typeof dbname === "function" ? '批量删除数据库' : `删除数据库 [ ${dbname} ]`;
                    
                    // 简化的确认对话框
                    layer.open({
                        type: 1,
                        title: title,
                        icon: 0,
                        skin: 'delete_site_layer',
                        area: "530px",
                        closeBtn: 2,
                        shadeClose: true,
                        content: `<div class='bt-form webDelete pd30' id='site_delete_form'>
                            <i class='layui-layer-ico layui-layer-ico0'></i>
                            <div class='f13 check_title' style='margin-bottom: 20px;'>是否确认【删除数据库】，删除后可能会影响业务使用！</div>
                            <div style='color:red;margin:18px 0 18px 18px;font-size:14px;font-weight: bold;'>注意：数据无价，请谨慎操作！！！${!recycle_bin_db_open ? '<br>风险操作：当前数据库回收站未开启，删除数据库将永久消失！' : ''}</div>
                        </div>`,
                        btn: [lan?.public?.ok || '确定', lan?.public?.cancel || '取消'],
                        yes: function(indexs) {
                            const data = { id: wid, name: dbname };
                            if (typeof dbname === "function") {
                                delete data.id;
                                delete data.name;
                            }
                            layer.close(indexs);
                            
                            if (typeof dbname === "function") {
                                dbname(data);
                            } else {
                                bt.database.del_database(data, function(rdata) {
                                    layer.closeAll();
                                    if (rdata.status) database.database_table_view();
                                    if (callback) callback(rdata);
                                    bt.msg(rdata);
                                });
                            }
                        }
                    });
                };
            }
        }
        
        // 设置站点操作覆盖
        setupSiteOverrides() {
            if (typeof site !== 'undefined' && site.hasOwnProperty('del_site')) {
                this.overrides.set('site.del_site', site.del_site);
                
                site.del_site = function(wid, wname, callback) {
                    Utils.log('Intercepted site.del_site call');
                    
                    const title = typeof wname === "function" ? '批量删除站点' : `删除站点 [ ${wname} ]`;
                    
                    layer.open({
                        type: 1,
                        title: title,
                        icon: 0,
                        skin: 'delete_site_layer',
                        area: "440px",
                        closeBtn: 2,
                        shadeClose: true,
                        content: `<div class='bt-form webDelete pd30' id='site_delete_form'>
                            <i class="layui-layer-ico layui-layer-ico0"></i>
                            <div class='f13 check_title'>是否要删除关联的FTP、数据库、站点目录！</div>
                            <div class="check_type_group">
                                <label><input type="checkbox" name="ftp"><span>FTP</span></label>
                                <label><input type="checkbox" name="database"><span>数据库</span>${!recycle_bin_db_open ? '<span class="glyphicon glyphicon-info-sign" style="color: red"></span>' : ''}</label>
                                <label><input type="checkbox" name="path"><span>站点目录</span>${!recycle_bin_open ? '<span class="glyphicon glyphicon-info-sign" style="color: red"></span>' : ''}</label>
                            </div>
                        </div>`,
                        btn: [lan?.public?.ok || '确定', lan?.public?.cancel || '取消'],
                        yes: function(indexs) {
                            const data = { id: wid, name: wname };
                            if (typeof wname === "function") {
                                delete data.id;
                                delete data.name;
                            }
                            layer.close(indexs);
                            
                            if (typeof wname === "function") {
                                wname(data);
                            } else {
                                bt.site.del_site(data, function(rdata) {
                                    layer.closeAll();
                                    if (rdata.status) site.site_table_view();
                                    if (callback) callback(rdata);
                                    bt.msg(rdata);
                                });
                            }
                        }
                    });
                };
            }
        }
        
        // 设置安全消息覆盖
        setupSafeMessageOverride() {
            // 覆盖全局的SafeMessage函数
            window.SafeMessage = function(j, h, g, f) {
                Utils.log('Intercepted SafeMessage call');
                
                // 立即执行回调，跳过验证
                if (f && typeof f === 'function') {
                    setTimeout(() => {
                        try {
                            f();
                        } catch (e) {
                            Utils.handleError(e, 'SafeMessage callback');
                        }
                    }, CONFIG.DELAY_TIMEOUT);
                }
                
                // 可选：显示简化的验证对话框
                if (CONFIG.DEBUG) {
                    layer.open({
                        type: 1,
                        title: h || '验证',
                        area: "300px",
                        closeBtn: 2,
                        btn: ['确认', '取消'],
                        content: `<div class='bt-form pd20'>
                            <p>${g || '请确认操作'}</p>
                        </div>`,
                        yes: function(index) {
                            layer.close(index);
                            if (f) f();
                        }
                    });
                }
            };
        }
        
        // 移除延时等待
        setupDelayRemoval() {
            // 覆盖setTimeout以移除不必要的延时
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(callback, delay, ...args) {
                // 对于非常短的延时（可能是验证延时），直接执行
                if (delay < 1000 && typeof callback === 'function') {
                    Utils.log(`Removed delay: ${delay}ms`);
                    return originalSetTimeout(callback, CONFIG.DELAY_TIMEOUT, ...args);
                }
                return originalSetTimeout(callback, delay, ...args);
            };
            
            // 覆盖setInterval以优化轮询
            const originalSetInterval = window.setInterval;
            window.setInterval = function(callback, delay, ...args) {
                // 对于过短的轮询间隔，适当延长
                if (delay < 100 && typeof callback === 'function') {
                    Utils.log(`Optimized interval: ${delay}ms -> 1000ms`);
                    return originalSetInterval(callback, 1000, ...args);
                }
                return originalSetInterval(callback, delay, ...args);
            };
        }
        
        // 恢复原始函数
        restore() {
            this.overrides.forEach((originalFunc, path) => {
                const pathParts = path.split('.');
                const obj = pathParts.slice(0, -1).reduce((current, key) => current[key], window);
                const funcName = pathParts[pathParts.length - 1];
                obj[funcName] = originalFunc;
            });
            
            // 恢复setTimeout和setInterval
            if (window._originalSetTimeout) {
                window.setTimeout = window._originalSetTimeout;
                delete window._originalSetTimeout;
            }
            if (window._originalSetInterval) {
                window.setInterval = window._originalSetInterval;
                delete window._originalSetInterval;
            }
            
            Utils.log('Original functions restored');
        }
        
        // 获取状态信息
        getStatus() {
            return {
                initialized: this.initialized,
                overridesCount: this.overrides.size,
                version: CONFIG.VERSION,
                debug: CONFIG.DEBUG
            };
        }
    }
    
    // 初始化优化器
    let optimizer;
    
    // 等待DOM加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            optimizer = new BTOptimizer();
        });
    } else {
        optimizer = new BTOptimizer();
    }
    
    // 暴露到全局作用域
    window.BTOptimizer = {
        instance: optimizer,
        CONFIG: CONFIG,
        Utils: Utils,
        getStatus: () => optimizer ? optimizer.getStatus() : null,
        restore: () => optimizer ? optimizer.restore() : null
    };
    
    Utils.log('BT Optimizer script loaded');
    
})();