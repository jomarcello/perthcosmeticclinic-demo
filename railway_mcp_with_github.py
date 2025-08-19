#!/usr/bin/env python3
"""
Complete Railway MCP Client met GitHub repository creation
"""

import asyncio
import json
import sys
import os
import subprocess
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from urllib.parse import urlencode

class CompleteWorkflowMCPClient:
    def __init__(self):
        # Railway MCP config
        self.base_url = "https://server.smithery.ai/@jason-tan-swe/railway-mcp/mcp"
        self.smithery_params = {
            "api_key": "2f9f056b-67dc-47e1-b6c4-79c41bf85d07", 
            "profile": "zesty-clam-4hb4aa"
        }
        self.url = f"{self.base_url}?{urlencode(self.smithery_params)}"
        
        # GitHub config (needs to be set via environment)
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable required")
        
    def create_github_repo(self, practice_data):
        """Create new GitHub repository for practice"""
        repo_name = f"{practice_data['practice_id']}-demo"
        
        try:
            # 1. Create new repository via GitHub API
            create_cmd = [
                'curl', '-X', 'POST',
                '-H', f'Authorization: token {self.github_token}',
                '-H', 'Accept: application/vnd.github.v3+json',
                'https://api.github.com/user/repos',
                '-d', json.dumps({
                    'name': repo_name,
                    'description': f'Healthcare demo for {practice_data["company"]}',
                    'private': False,
                    'auto_init': True
                })
            ]
            
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"success": False, "error": f"GitHub API error: {result.stderr}"}
                
            repo_data = json.loads(result.stdout)
            
            if 'clone_url' not in repo_data:
                return {"success": False, "error": f"GitHub API response invalid: {result.stdout}"}
            
            # 2. Clone template and personalize
            template_path = "/app"  # Current directory has template
            repo_path = f"/tmp/{repo_name}"
            
            # Clone the new empty repo
            subprocess.run(['git', 'clone', repo_data['clone_url'], repo_path], check=True)
            
            # Copy template files (skip git folder and sensitive files)
            subprocess.run([
                'rsync', '-av', 
                '--exclude=.git', '--exclude=node_modules', '--exclude=.next', '--exclude=.env',
                f'{template_path}/', f'{repo_path}/'
            ], check=True)
            
            # 3. Personalize the code
            self.personalize_repo(repo_path, practice_data)
            
            # 4. Commit and push with authentication
            os.chdir(repo_path)
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run([
                'git', 'commit', '-m', 
                f'🎯 Personalized demo for {practice_data["company"]}'
            ], check=True)
            
            # Set authenticated remote URL
            auth_url = f"https://{self.github_token}@github.com/jomarcello/{repo_name}.git"
            subprocess.run(['git', 'remote', 'set-url', 'origin', auth_url], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            return {
                "success": True,
                "repo_name": repo_name,
                "repo_url": repo_data['html_url'],
                "clone_url": repo_data['clone_url']
            }
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Git operation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Repository creation failed: {e}"}
    
    def personalize_repo(self, repo_path, practice_data):
        """Personalize template with practice-specific data"""
        
        # Create practice config file
        config_content = f"""
export const practiceConfig = {{
    id: '{practice_data['practice_id']}',
    name: '{practice_data['company']}',
    doctor: '{practice_data.get('doctor', 'Dr. Smith')}',
    location: '{practice_data.get('location', 'London')}',
    specialization: '{practice_data.get('specialization', 'General Practice')}',
    phone: '{practice_data.get('phone', '+44 20 1234 5678')}',
    email: '{practice_data.get('email', 'info@practice.com')}',
    website: '{practice_data.get('website', 'https://practice.com')}',
}};
"""
        
        # Write config file
        with open(f"{repo_path}/src/lib/practice-config.ts", 'w') as f:
            f.write(config_content)
        
        # Update package.json name
        package_json_path = f"{repo_path}/package.json"
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            package_data['name'] = f"{practice_data['practice_id']}-demo"
            package_data['description'] = f"Healthcare demo for {practice_data['company']}"
            
            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
    
    async def _execute_mcp_call(self, tool_name, params=None):
        """Execute MCP tool call with proper error handling"""
        try:
            async with streamablehttp_client(self.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, params or {})
                    
                    if hasattr(result, 'content') and result.content:
                        content = result.content[0].text if result.content[0] else str(result)
                        return {"success": True, "data": content}
                    else:
                        return {"success": True, "data": str(result)}
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_complete_deployment(self, practice_data):
        """Create complete deployment: GitHub repo + Railway deployment"""
        
        try:
            # Step 1: Create personalized GitHub repository
            repo_result = self.create_github_repo(practice_data)
            if not repo_result["success"]:
                return {"success": False, "error": f"GitHub repo creation failed: {repo_result['error']}"}
            
            # Step 2: Create Railway project
            project_name = f"{practice_data['practice_id']}-demo"
            project_result = await self._execute_mcp_call("project_create", {
                "name": project_name
            })
            
            if not project_result["success"]:
                return {"success": False, "error": f"Railway project creation failed: {project_result['error']}"}
                
            # Extract project ID
            project_data = project_result["data"]
            if "ID:" in project_data:
                project_id = project_data.split("ID: ")[1].split(")")[0]
            else:
                return {"success": False, "error": "Could not extract project ID"}
            
            # Step 3: Get environment
            env_result = await self._execute_mcp_call("project_environments", {
                "projectId": project_id
            })
            
            if not env_result["success"]:
                return {"success": False, "error": f"Environment fetch failed: {env_result['error']}"}
                
            env_data = env_result["data"]
            if "ID:" in env_data:
                environment_id = env_data.split("ID: ")[1].split(")")[0]
            else:
                return {"success": False, "error": "Could not extract environment ID"}
            
            # Step 4: Create service from NEW GitHub repo
            service_result = await self._execute_mcp_call("service_create_from_repo", {
                "projectId": project_id,
                "repo": f"jomarcello/{repo_result['repo_name']}",  # Use NEW repo
                "name": f"{practice_data['practice_id']}-service"
            })
            
            if not service_result["success"]:
                return {"success": False, "error": f"Service creation failed: {service_result['error']}"}
                
            # Extract service ID
            service_data = service_result["data"]
            if "ID:" in service_data:
                service_id = service_data.split("ID: ")[1].split(")")[0]
            else:
                return {"success": False, "error": "Could not extract service ID"}
            
            # Step 5: Create domain
            domain_result = await self._execute_mcp_call("domain_create", {
                "environmentId": environment_id,
                "serviceId": service_id
            })
            
            if not domain_result["success"]:
                return {"success": False, "error": f"Domain creation failed: {domain_result['error']}"}
                
            # Extract domain URL
            domain_data = domain_result["data"]
            if ".up.railway.app" in domain_data:
                lines = domain_data.split('\n')
                for line in lines:
                    if ".up.railway.app" in line:
                        domain_url = line.split(":")[1].strip().split(" ")[0]
                        break
                else:
                    return {"success": False, "error": "Could not extract domain URL"}
            else:
                return {"success": False, "error": "No Railway domain found in response"}
                
            full_url = f"https://{domain_url}"
            
            return {
                "success": True,
                "github_repo": repo_result['repo_url'],
                "project_id": project_id,
                "environment_id": environment_id,
                "service_id": service_id,
                "domain_url": full_url,
                "deployment_status": "complete_new_repo"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: railway_mcp_with_github.py create_complete_workflow <params>"}))
        sys.exit(1)
    
    action = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    client = CompleteWorkflowMCPClient()
    
    if action == "create_complete_workflow":
        # Convert clinic_name to practice data
        clinic_name = params.get("clinic_name", "Test Clinic")
        practice_data = {
            "practice_id": clinic_name.lower().replace(' ', '').replace('.', ''),
            "company": clinic_name,
            "doctor": f"Dr. {clinic_name.split()[0]} Smith",
            "location": "London",
            "specialization": "Healthcare"
        }
        
        result = await client.create_complete_deployment(practice_data)
    else:
        result = {"success": False, "error": f"Unknown action: {action}"}
    
    print(json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())