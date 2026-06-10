import axios from 'axios'

// 配置axios基础URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// 获取用户ID（从 localStorage 读取，没有则生成）
function getUserId() {
    let uid = localStorage.getItem('aich_userId')
    if (!uid) {
        uid = 'user_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8)
        localStorage.setItem('aich_userId', uid)
    }
    return uid
}

/**
 * 调用智能体对话接口（非流式）
 * @param {string} message 用户消息
 * @returns {Promise<Object>} 返回智能体的响应
 */
export async function chatWithAgent(message) {
    try {
        const response = await axios.post(`${API_BASE_URL}/agent/chat`, {
            message: message,
            userId: getUserId()
        }, {
            timeout: 180000 // 3分钟超时
        })
        return response.data
    } catch (error) {
        console.error('智能体对话失败:', error)
        throw error
    }
}

/**
 * 获取智能体可用的工具列表
 * @returns {Promise<Object>} 工具列表（含分类）
 */
export async function getAgentTools() {
    try {
        const response = await axios.get(`${API_BASE_URL}/agent/tools`, { timeout: 5000 })
        return response.data
    } catch (error) {
        console.error('获取工具列表失败:', error)
        return { tools: [], total: 0 }
    }
}

/**
 * RAG 检索 - 从知识库和偏好中搜索
 * @param {string} query 搜索关键词
 * @param {number} maxResults 最大结果数
 * @returns {Promise<Object>} 检索结果
 */
export async function searchKnowledge(query, maxResults = 5) {
    try {
        const response = await axios.get(`${API_BASE_URL}/agent/search`, {
            params: { query, maxResults },
            timeout: 15000
        })
        return response.data
    } catch (error) {
        console.error('RAG检索失败:', error)
        return { result: '', isEmpty: true }
    }
}

/**
 * 获取用户偏好
 * @returns {Promise<Object>} 用户偏好数据
 */
export async function getUserPreferences() {
    try {
        const response = await axios.get(`${API_BASE_URL}/preferences/${getUserId()}`, {
            timeout: 10000
        })
        return response.data
    } catch (error) {
        console.error('获取偏好失败:', error)
        return { savedPreferences: [], inferredPreferences: {}, systemDefaults: [] }
    }
}

/**
 * 获取系统上下文摘要
 * @returns {Promise<Object>}
 */
export async function getSystemContext() {
    try {
        const response = await axios.get(`${API_BASE_URL}/preferences/context`, { timeout: 5000 })
        return response.data
    } catch (error) {
        console.error('获取系统上下文失败:', error)
        return { systemContext: '', isEmpty: true }
    }
}

/**
 * 获取记忆统计
 * @returns {Promise<Object>}
 */
export async function getMemoryStats() {
    try {
        const response = await axios.get(`${API_BASE_URL}/agent/memory/stats`, {
            params: { userId: getUserId() },
            timeout: 5000
        })
        return response.data
    } catch (error) {
        console.error('获取记忆统计失败:', error)
        return { '总记忆条数': 0, '短时记忆条数': 0, '长时摘要条数': 0 }
    }
}

/**
 * 清除短时记忆（新建会话）
 * @returns {Promise<Object>}
 */
export async function clearMemory() {
    try {
        const response = await axios.post(`${API_BASE_URL}/agent/memory/clear`, {
            userId: getUserId()
        }, { timeout: 5000 })
        return response.data
    } catch (error) {
        console.error('清除记忆失败:', error)
        throw error
    }
}

/**
 * 获取所有已生成的文件列表
 */
export async function getGeneratedFiles() {
    try {
        const response = await axios.get(`${API_BASE_URL}/files/list`, { timeout: 10000 })
        return response.data
    } catch (error) {
        console.error('获取文件列表失败:', error)
        return { files: [], total: 0 }
    }
}

/**
 * 获取文件内容（Base64）
 */
export async function getFileContent(fileName) {
    try {
        const response = await axios.get(`${API_BASE_URL}/files/content/${encodeURIComponent(fileName)}`, {
            timeout: 30000
        })
        return response.data
    } catch (error) {
        console.error('获取文件内容失败:', error)
        throw error
    }
}

/**
 * 删除指定文件
 */
export async function deleteGeneratedFile(fileName) {
    try {
        const response = await axios.delete(`${API_BASE_URL}/files/${encodeURIComponent(fileName)}`, {
            timeout: 10000
        })
        return response.data
    } catch (error) {
        console.error('删除文件失败:', error)
        throw error
    }
}
