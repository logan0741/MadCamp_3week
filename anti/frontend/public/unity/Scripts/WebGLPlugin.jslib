mergeInto(LibraryManager.library, {
    /**
     * Unity에서 JavaScript로 메시지 전송
     * WebGLBridge.cs의 SendMessageToJS에서 호출됨
     */
    SendMessageToJS: function(messagePtr) {
        var message = UTF8ToString(messagePtr);
        
        try {
            var data = JSON.parse(message);
            
            // Custom event dispatch for react-unity-webgl
            var event = new CustomEvent('unityMessage', {
                detail: data
            });
            window.dispatchEvent(event);
            
            // Console log for debugging
            console.log('[Unity → JS]', data);
            
        } catch (e) {
            console.error('[Unity → JS] Parse error:', e);
        }
    }
});
