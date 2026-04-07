#!/usr/bin/env python3
"""
安全检查脚本：扫描 git 暂存区中的敏感信息。
用法：在 git 仓库根目录运行 python scripts/security_check.py
退出码：0 = 未发现问题，1 = 发现可疑内容
"""

import re
import subprocess
import sys

# 敏感信息匹配规则
PATTERNS = [
    # API Keys & Tokens
    (r'(?i)(api[_-]?key|api[_-]?secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}', "API 密钥"),
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI 风格密钥 (sk-...)"),
    (r'ghp_[A-Za-z0-9]{36,}', "GitHub Personal Access Token"),
    (r'gho_[A-Za-z0-9]{36,}', "GitHub OAuth Token"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}', "Bearer Token"),

    # Passwords & Secrets
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?.{6,}', "密码字段"),
    (r'(?i)(secret|token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{8,}', "Secret/Token 赋值"),

    # Private Keys
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "私钥文件内容"),
    (r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----', "EC 私钥文件内容"),

    # Connection Strings
    (r'(?i)(mysql|postgres|mongodb|redis)://[^\s]+@[^\s]+', "数据库连接串"),

    # Debug leftovers (Go-specific)
    (r'fmt\.Print(ln|f)?\s*\(\s*"debug', "调试输出 (fmt.Print)"),
    (r'log\.(Debug|Print)(ln|f)?\s*\(.*TODO', "调试日志 (含 TODO)"),
    (r'//\s*TODO:\s*remove', "TODO: remove 注释"),

    # Internal IPs
    (r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b', "内网 IP 地址"),
]


def get_staged_diff():
    """获取暂存区 diff 内容"""
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"错误：无法获取暂存区 diff: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def scan_diff(diff_text):
    """扫描 diff 中的敏感信息，只检查新增行（以 + 开头）"""
    findings = []
    lines = diff_text.split("\n")
    current_file = ""

    for i, line in enumerate(lines):
        # 追踪当前文件
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # 只检查新增的行（忽略 diff header）
        if not line.startswith("+") or line.startswith("+++"):
            continue

        content = line[1:]  # 去掉 + 前缀

        for pattern, desc in PATTERNS:
            if re.search(pattern, content):
                findings.append({
                    "file": current_file,
                    "line": content.strip(),
                    "type": desc,
                })
                break  # 一行只报告一次

    return findings


def main():
    diff = get_staged_diff()

    if not diff.strip():
        print("暂存区为空，无需检查。")
        sys.exit(0)

    findings = scan_diff(diff)

    if not findings:
        print("✅ 安全检查通过：未发现敏感信息。")
        sys.exit(0)

    print(f"⚠️  发现 {len(findings)} 处可疑内容：\n")
    for f in findings:
        print(f"  📁 文件: {f['file']}")
        print(f"  🏷️  类型: {f['type']}")
        print(f"  📝 内容: {f['line'][:120]}...")
        print()

    print("请确认以上内容是否应该被提交。")
    print("如需排除某个文件：git reset HEAD <file>")
    sys.exit(1)


if __name__ == "__main__":
    main()
