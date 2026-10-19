# 导入所有模型，确保 Base.metadata 注册全部表
from app.models.user import User
from app.models.project import Project
from app.models.prd import PrdDocument, Requirement
from app.models.plan import TestPlan
from app.models.testcase import TestCase, TestCaseStep, CaseRequirement
from app.models.execution import TestExecution
from app.models.bug import Bug, BugComment
from app.models.automation import AutomationScript, AutomationTask
from app.models.release import Version, Environment
from app.models.knowledge import KnowledgeDoc
from app.models.ai import ModelConfig, Skill, PromptTemplate
from app.models.operation_log import OperationLog
from app.models.tracking import TrackingEvent, TrackingConfig
from app.models.apitest import ApiCase, ApiEnv

__all__ = [
    "User", "Project", "PrdDocument", "Requirement", "TestPlan",
    "TestCase", "TestCaseStep", "CaseRequirement", "TestExecution",
    "Bug", "BugComment", "AutomationScript", "AutomationTask",
    "Version", "Environment", "KnowledgeDoc", "ModelConfig", "Skill",
    "PromptTemplate", "OperationLog", "TrackingEvent", "TrackingConfig",
    "ApiCase", "ApiEnv",
]
