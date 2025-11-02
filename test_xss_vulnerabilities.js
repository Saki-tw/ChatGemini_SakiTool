// 測試 XSS 漏洞掃描器的範例檔案
// 包含多種 XSS 攻擊場景

// ==================== XSS 漏洞 ====================

// 1. innerHTML 漏洞
function displayUserComment(comment) {
    // 危險: 直接設置 innerHTML
    const div = document.getElementById('comment');
    div.innerHTML = comment;
}

function showUserProfile(profileHtml) {
    // 危險: 直接插入使用者提供的 HTML
    document.getElementById('profile').innerHTML = profileHtml;
}

// 2. outerHTML 漏洞
function replaceElement(newHtml) {
    // 危險: 替換整個元素
    const element = document.getElementById('target');
    element.outerHTML = newHtml;
}

// 3. document.write() 漏洞
function showMessage(message) {
    // 危險: 使用 document.write
    document.write('<div>' + message + '</div>');
}

function displayAd(adCode) {
    // 危險: 直接寫入廣告程式碼
    document.write(adCode);
}

// 4. eval() 漏洞 - 極度危險
function executeUserCode(code) {
    // 危險: 執行使用者提供的程式碼
    eval(code);
}

function calculateExpression(expr) {
    // 危險: 動態計算表達式
    const result = eval('(' + expr + ')');
    return result;
}

// 5. insertAdjacentHTML 漏洞
function addNotification(notificationHtml) {
    // 危險: 插入未清理的 HTML
    const container = document.getElementById('notifications');
    container.insertAdjacentHTML('beforeend', notificationHtml);
}

// 6. React dangerouslySetInnerHTML 漏洞
function UserComment({ comment }) {
    // 危險: React 的危險 API
    return (
        <div dangerouslySetInnerHTML={{__html: comment}} />
    );
}

function BlogPost({ content }) {
    // 危險: 直接渲染使用者內容
    return (
        <article dangerouslySetInnerHTML={{__html: content}} />
    );
}

// ==================== 安全的程式碼（應被排除）====================

// 1. 使用 textContent - 安全
function displayUserCommentSafe(comment) {
    // 安全: 使用 textContent
    const div = document.getElementById('comment');
    div.textContent = comment;
}

// 2. 使用 createElement - 安全
function addCommentSafe(text) {
    // 安全: 手動建立元素
    const div = document.createElement('div');
    div.textContent = text;
    document.getElementById('comments').appendChild(div);
}

// 3. 使用 DOMPurify - 安全
function displayUserCommentWithPurify(comment) {
    // 安全: 使用 DOMPurify 清理
    const div = document.getElementById('comment');
    div.innerHTML = DOMPurify.sanitize(comment);
}

// 4. React 安全渲染
function UserCommentSafe({ comment }) {
    // 安全: React 自動轉義
    return <div>{comment}</div>;
}

// 5. 使用 JSON.parse 取代 eval - 安全
function parseUserData(jsonString) {
    // 安全: 使用 JSON.parse
    try {
        const data = JSON.parse(jsonString);
        return data;
    } catch (e) {
        console.error('Invalid JSON');
        return null;
    }
}

// ==================== 複雜的 XSS 場景 ====================

class CommentManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    // 危險: 類別方法中的 innerHTML
    addComment(username, comment) {
        const html = `
            <div class="comment">
                <strong>${username}</strong>
                <p>${comment}</p>
            </div>
        `;
        this.container.innerHTML += html;
    }

    // 危險: 使用模板字串
    renderTemplate(data) {
        this.container.innerHTML = `
            <h2>${data.title}</h2>
            <div>${data.content}</div>
        `;
    }

    // 安全: 使用 DOM API
    addCommentSafe(username, comment) {
        const div = document.createElement('div');
        div.className = 'comment';

        const strong = document.createElement('strong');
        strong.textContent = username;

        const p = document.createElement('p');
        p.textContent = comment;

        div.appendChild(strong);
        div.appendChild(p);
        this.container.appendChild(div);
    }
}

// ==================== 動態腳本載入 ====================

function loadUserScript(scriptUrl) {
    // 危險: 動態載入腳本
    const script = document.createElement('script');
    script.src = scriptUrl;  // 如果 URL 來自使用者輸入，這是危險的
    document.head.appendChild(script);
}

function injectInlineScript(code) {
    // 危險: 注入行內腳本
    const script = document.createElement('script');
    script.innerHTML = code;
    document.body.appendChild(script);
}

// ==================== 事件處理器 XSS ====================

function setClickHandler(elementId, handlerCode) {
    // 危險: 動態設置事件處理器
    const element = document.getElementById(elementId);
    element.setAttribute('onclick', handlerCode);
}

// ==================== URL 操作 ====================

function redirectUser(url) {
    // 潛在危險: 如果 URL 來自使用者輸入
    // javascript: URL 可能導致 XSS
    window.location.href = url;
}

function openUserLink(url) {
    // 危險: 使用 eval 建構 URL
    eval("window.open('" + url + "')");
}

// ==================== 第三方函式庫整合 ====================

// jQuery XSS 範例
function displayWithJQuery(content) {
    // 危險: jQuery .html() 方法
    $('#content').html(content);
}

function appendWithJQuery(item) {
    // 危險: jQuery append 使用 HTML 字串
    $('#list').append('<li>' + item + '</li>');
}

// 安全的 jQuery 使用
function displayWithJQuerySafe(content) {
    // 安全: jQuery .text() 方法
    $('#content').text(content);
}
