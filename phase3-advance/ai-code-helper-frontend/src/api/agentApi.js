import axios from 'axios'

// 配置axios基础URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8081/api'

/**
 * 调用智能体对话接口（非流式）
 * @param {string} message 用户消息
 * @returns {Promise<Object>} 返回智能体的响应，包含思考过程和最终答案
 */
export async function chatWithAgent(message) {
    try {
        const response = await axios.post(`${API_BASE_URL}/agent/chat`, {
            message: message
        }, {
            timeout: 120000 // 智能体可能需要更长时间（2分钟）
        })
        return response.data
    } catch (error) {
        console.error('智能体对话失败:', error)
        throw error
    }
}

/**
 * 获取智能体可用的工具列表
 * @returns {Promise<Array>} 工具列表
 */
export async function getAgentTools() {
    try {
        const response = await axios.get(`${API_BASE_URL}/agent/tools`, {
            timeout: 5000
        })
        return response.data
    } catch (error) {
        console.error('获取工具列表失败:', error)
        return []
    }
}

/**
 * 获取所有已生成的文件列表
 * @returns {Promise<Object>} 文件列表
 */
export async function getGeneratedFiles() {
    try {
        const response = await axios.get(`${API_BASE_URL}/files/list`, {
            timeout: 10000
        })
        return response.data
    } catch (error) {
        console.error('获取文件列表失败:', error)
        return { files: [], total: 0 }
    }
}

/**
 * 获取文件内容（Base64）
 * @param {string} fileName 文件名
 * @returns {Promise<Object>} 文件内容
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
 * @param {string} fileName 文件名
 * @returns {Promise<Object>} 删除结果
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
