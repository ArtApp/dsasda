"""
Модуль NLP-анализа для улучшения понимания контекста в описательной части проектов.
Использует spaCy и pymorphy3 для обработки русского текста и извлечения семантической информации.
"""

import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    import spacy
    import pymorphy3
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


class EntityCategory(Enum):
    """Категории извлекаемых сущностей."""
    DEVICE = "DEVICE"  # Устройства (С2000М, КДЛ, ДИП, ИПР и т.д.)
    LOCATION = "LOCATION"  # Помещения, зоны размещения
    QUANTITY = "QUANTITY"  # Количество устройств
    ADDRESS = "ADDRESS"  # Адреса устройств (ARK, SC, BTH)
    PARAMETER = "PARAMETER"  # Параметры (версия, алгоритм, тип)
    ACTION = "ACTION"  # Действия (управление, активация)
    CONNECTION = "CONNECTION"  # Подключения, связи между устройствами


@dataclass
class ExtractedEntity:
    """Извлеченная сущность из текста."""
    text: str  # Исходный текст сущности
    category: EntityCategory  # Категория сущности
    normalized_form: str  # Нормализованная форма (лемма)
    confidence: float  # Уверенность извлечения (0.0-1.0)
    context: str = ""  # Контекст вокруг сущности
    metadata: dict = field(default_factory=dict)  # Дополнительные данные
    
    def __post_init__(self):
        if not self.normalized_form:
            self.normalized_form = self.text


@dataclass
class NLPAnalysisResult:
    """Результат NLP-анализа текста."""
    entities: list[ExtractedEntity] = field(default_factory=list)
    device_mentions: list[ExtractedEntity] = field(default_factory=list)
    location_mentions: list[ExtractedEntity] = field(default_factory=list)
    quantity_mentions: list[ExtractedEntity] = field(default_factory=list)
    address_mentions: list[ExtractedEntity] = field(default_factory=list)  # Добавлено
    relations: list[dict] = field(default_factory=list)  # Связи между сущностями
    summary: str = ""  # Краткое содержание
    warnings: list[str] = field(default_factory=list)
    
    def add_entity(self, entity: ExtractedEntity):
        """Добавить сущность в результат."""
        self.entities.append(entity)
        
        # Категоризация по типам
        if entity.category == EntityCategory.DEVICE:
            self.device_mentions.append(entity)
        elif entity.category == EntityCategory.LOCATION:
            self.location_mentions.append(entity)
        elif entity.category == EntityCategory.QUANTITY:
            self.quantity_mentions.append(entity)
        elif entity.category == EntityCategory.ADDRESS:
            self.address_mentions.append(entity)  # Добавлено


class RussianNLPAnalyzer:
    """
    Анализатор текста на русском языке с использованием spaCy и pymorphy3.
    Предназначен для извлечения сущностей из проектной документации систем безопасности.
    """
    
    # Паттерны устройств «Болид»
    DEVICE_PATTERNS = {
        's2000m': r'С2000[−-]?М(?:\s*исп\.?\d+)?',
        'kdl': r'С2000[−-]?КДЛ[−-]?2И(?:\s*исп\.?\d+)?',
        'sp2': r'С2000[−-]?СП2(?:\s*исп\.?\d+)?',
        'bki': r'С2000[−-]?БКИ(?:\s*исп\.?\d+)?',
        'dip': r'ДИП[−-]?34[А-Я]?(?:[−-]?\d+)?',
        'ipr': r'ИПР\s*513[−-]?[3ЗАМ]+(?:\s*исп\.?\d+)?',
        'ipdl': r'С2000[−-]?ИПДЛ',
        'rs200t': r'RS?[−-]?200Т?',
        'siren': r'[Сс]ирена(?:\s*[Зз]вуковая)?',
        'tablo': r'[Тт]абло(?:\s*[Сс]ветовое)?',
        'mayak': r'[Мм]аяк[−-]?\d+[−-]?[3М]?',
    }
    
    # Паттерны адресов
    ADDRESS_PATTERNS = [
        r'ARK\d+',      # ARK1, ARK2, etc.
        r'SC\d+[−-]\d+', # SC39-40, SC41-42
        r'BTH\d+',      # BTH1, BTH2, etc.
        r'адрес\s*\d+', # адрес 1, адрес 2
        r'№\s*\d+',     # №1, №2
    ]
    
    # Ключевые слова для локаций
    LOCATION_KEYWORDS = [
        'помещение', 'комната', 'коридор', 'холл', 'этаж', 'здание',
        'склад', 'офис', 'кабинет', 'зал', 'цех', 'участок',
        'вход', 'выход', 'эвакуационный выход', 'запасный выход',
        'лестничная клетка', 'лифт', 'тамбур', 'вестибюль'
    ]
    
    # Ключевые слова для количеств
    QUANTITY_KEYWORDS = [
        'шт', 'штука', 'штуки', 'единиц', 'комплект', 'комплектов',
        'количество', 'число', 'всего'
    ]
    
    def __init__(self, use_spacy: bool = True):
        """
        Инициализация анализатора.
        
        Args:
            use_spacy: Использовать ли spaCy для глубокого анализа
        """
        self.nlp = None
        
        if NLP_AVAILABLE:
            try:
                import pymorphy3
                self.morph = pymorphy3.MorphAnalyzer()
            except (ImportError, NameError):
                self.morph = None
                print("⚠ pymorphy3 недоступен")
        else:
            self.morph = None
            print("⚠ NLP библиотеки недоступны")
        
        if use_spacy and NLP_AVAILABLE:
            try:
                self.nlp = spacy.load('ru_core_news_sm')
                print("✓ spaCy модель ru_core_news_sm загружена")
            except OSError:
                print("⚠ Модель ru_core_news_sm не найдена. Запустите: python -m spacy download ru_core_news_sm")
                self.nlp = None
        else:
            print("ℹ spaCy отключен, используется только pymorphy3")
    
    def analyze_text(self, text: str) -> NLPAnalysisResult:
        """
        Полный анализ текста проектной документации.
        
        Args:
            text: Текст для анализа
            
        Returns:
            NLPAnalysisResult с извлеченными сущностями
        """
        result = NLPAnalysisResult()
        
        if not text.strip():
            result.warnings.append("Пустой текст для анализа")
            return result
        
        # Извлечение сущностей через паттерны
        self._extract_device_entities(text, result)
        self._extract_address_entities(text, result)
        self._extract_quantity_entities(text, result)
        self._extract_location_entities(text, result)
        
        # Глубокий анализ с spaCy
        if self.nlp:
            self._spacy_analysis(text, result)
        
        # Поиск связей между сущностями
        self._extract_relations(text, result)
        
        # Генерация краткого содержания
        result.summary = self._generate_summary(result)
        
        return result
    
    def _extract_device_entities(self, text: str, result: NLPAnalysisResult):
        """Извлечение упоминаний устройств."""
        for device_type, pattern in self.DEVICE_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                
                # Нормализация через pymorphy3
                normalized = self._normalize_text(matched_text)
                
                # Определение уверенности
                confidence = 0.9 if device_type in ['s2000m', 'kdl', 'dip', 'ipr'] else 0.7
                
                # Извлечение контекста (±50 символов)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                entity = ExtractedEntity(
                    text=matched_text,
                    category=EntityCategory.DEVICE,
                    normalized_form=normalized,
                    confidence=confidence,
                    context=context,
                    metadata={'device_type': device_type}
                )
                result.add_entity(entity)
    
    def _extract_address_entities(self, text: str, result: NLPAnalysisResult):
        """Извлечение адресов устройств."""
        for pattern in self.ADDRESS_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                normalized = self._normalize_text(matched_text)
                
                # Попытка извлечь числовое значение
                numbers = re.findall(r'\d+', matched_text)
                address_value = int(numbers[0]) if numbers else None
                
                entity = ExtractedEntity(
                    text=matched_text,
                    category=EntityCategory.ADDRESS,
                    normalized_form=normalized,
                    confidence=0.85,
                    metadata={'address_value': address_value}
                )
                result.add_entity(entity)
    
    def _extract_quantity_entities(self, text: str, result: NLPAnalysisResult):
        """Извлечение количественных упоминаний."""
        # Паттерн: число + единица измерения
        quantity_pattern = r'(\d+)\s*(?:шт|единиц?|комплектов?|наборов?)'
        
        for match in re.finditer(quantity_pattern, text, re.IGNORECASE):
            count = int(match.group(1))
            unit = match.group(2) if match.lastindex >= 2 else 'шт'
            
            # Контекст перед числом (что именно в этом количестве)
            start = max(0, match.start() - 100)
            context = text[start:match.end()].strip()
            
            entity = ExtractedEntity(
                text=match.group(0),
                category=EntityCategory.QUANTITY,
                normalized_form=f"{count} {unit}",
                confidence=0.95,
                context=context,
                metadata={'count': count, 'unit': unit}
            )
            result.add_entity(entity)
    
    def _extract_location_entities(self, text: str, result: NLPAnalysisResult):
        """Извлечение упоминаний местоположений."""
        words = text.split()
        
        for i, word in enumerate(words):
            word_lower = word.lower().strip('.,;:!?()[]{}\"\'')
            
            # Проверка на ключевые слова локации
            for keyword in self.LOCATION_KEYWORDS:
                if keyword in word_lower:
                    # Извлекаем фразу ±3 слова
                    start_idx = max(0, i - 3)
                    end_idx = min(len(words), i + 4)
                    phrase = ' '.join(words[start_idx:end_idx])
                    
                    normalized = self._normalize_text(word)
                    
                    entity = ExtractedEntity(
                        text=phrase,
                        category=EntityCategory.LOCATION,
                        normalized_form=normalized,
                        confidence=0.7,
                        metadata={'keyword': keyword}
                    )
                    result.add_entity(entity)
                    break
    
    def _spacy_analysis(self, text: str, result: NLPAnalysisResult):
        """Глубокий анализ с использованием spaCy."""
        if not self.nlp:
            return
        
        doc = self.nlp(text)
        
        # Анализ именованных сущностей (NER)
        for ent in doc.ents:
            # Пропускаем уже извлеченные паттернами
            if any(ent.text in e.text for e in result.entities):
                continue
            
            # Категоризация по типу сущности spaCy
            if ent.label_ in ['ORG', 'PRODUCT']:
                normalized = self._normalize_text(ent.text)
                entity = ExtractedEntity(
                    text=ent.text,
                    category=EntityCategory.DEVICE,
                    normalized_form=normalized,
                    confidence=0.6,  # Ниже уверенность для NER
                    metadata={'ner_label': ent.label_}
                )
                result.add_entity(entity)
        
        # Синтаксический анализ для поиска связей
        self._analyze_dependencies(doc, result)
    
    def _analyze_dependencies(self, doc, result: NLPAnalysisResult):
        """Анализ синтаксических зависимостей для выявления связей."""
        # Поиск конструкций типа "Устройство X в помещении Y"
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN']:
                # Ищем зависимые слова, указывающие на местоположение
                for child in token.children:
                    if child.dep_ == 'nmod' and child.text.lower() in self.LOCATION_KEYWORDS:
                        # Нашли связь устройство-местоположение
                        relation = {
                            'type': 'LOCATED_IN',
                            'source': token.text,
                            'target': child.text,
                            'confidence': 0.75
                        }
                        result.relations.append(relation)
    
    def _extract_relations(self, text: str, result: NLPAnalysisResult):
        """Извлечение связей между сущностями через паттерны."""
        # Паттерн: "Устройство -> действие -> объект"
        action_patterns = [
            r'([Сс]2000[^.]*?)\s*→\s*([^.]+)',  # Стрелка
            r'([Сс]2000[^.]*?)\s*[-–—]\s*([^.]+)',  # Тире
            r'([Сс]2000[^.]*?)\s*управляет\s*([^.]+)',  # "управляет"
            r'([Сс]2000[^.]*?)\s*включает\s*([^.]+)',  # "включает"
        ]
        
        for pattern in action_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1).strip()
                target = match.group(2).strip()
                
                relation = {
                    'type': 'CONTROLS',
                    'source': source,
                    'target': target,
                    'confidence': 0.8,
                    'pattern': pattern
                }
                result.relations.append(relation)
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста через лемматизацию."""
        if not text:
            return text
        
        # Используем pymorphy3 для лемматизации
        morph = self.morph
        lemmas = []
        
        # Разбиваем на слова и лемматизируем каждое
        words = re.findall(r'[\w\-]+', text)
        for word in words:
            parsed = morph.parse(word.upper())
            if parsed:
                lemmas.append(parsed[0].normal_form.lower())
            else:
                lemmas.append(word.lower())
        
        return ' '.join(lemmas)
    
    def _generate_summary(self, result: NLPAnalysisResult) -> str:
        """Генерация краткого содержания анализа."""
        parts = []
        
        if result.device_mentions:
            device_types = set(e.metadata.get('device_type', '') for e in result.device_mentions)
            parts.append(f"Найдено устройств: {len(result.device_mentions)} (типы: {', '.join(device_types)})")
        
        if result.address_mentions:
            parts.append(f"Найдено адресов: {len(result.address_mentions)}")
        
        if result.quantity_mentions:
            total_count = sum(e.metadata.get('count', 0) for e in result.quantity_mentions)
            parts.append(f"Общее количество устройств: ~{total_count}")
        
        if result.relations:
            parts.append(f"Выявлено связей: {len(result.relations)}")
        
        if result.warnings:
            parts.append(f"Предупреждений: {len(result.warnings)}")
        
        return "; ".join(parts) if parts else "Анализ не выявил значимых сущностей"
    
    def get_device_context(self, device_name: str, result: NLPAnalysisResult) -> list[str]:
        """
        Получение контекстных упоминаний конкретного устройства.
        
        Args:
            device_name: Название устройства для поиска
            result: Результат анализа
            
        Returns:
            Список контекстных фраз
        """
        contexts = []
        
        for entity in result.device_mentions:
            if device_name.lower() in entity.text.lower() or \
               device_name.lower() in entity.normalized_form.lower():
                if entity.context:
                    contexts.append(entity.context)
        
        return contexts


def analyze_project_description(text: str, use_spacy: bool = True) -> NLPAnalysisResult:
    """
    Удобная функция для анализа описания проекта.
    
    Args:
        text: Текст описания проекта
        use_spacy: Использовать ли spaCy
        
    Returns:
        NLPAnalysisResult с результатами анализа
    """
    analyzer = RussianNLPAnalyzer(use_spacy=use_spacy)
    return analyzer.analyze_text(text)


# Пример использования
if __name__ == "__main__":
    # Тестовый текст
    test_text = """
    В проекте используются следующие устройства:
    - С2000М исп.02 (адрес 127) - 1 шт, прибор приемно-контрольный
    - С2000-КДЛ-2И исп.01 (адрес 1) - 2 шт, контроллер двухпроводной линии связи
    - ДИП-34А-03 - 38 шт, извещатели пожарные дымовые, размещены в помещениях склада и офиса
    - ИПР 513-3АМ исп.01 - 5 шт, извещатели ручные, установлены у выходов
    - С2000-СП2 исп.01 - 5 шт, табло световые
    - С2000-БКИ - 1 шт, блок коммутации
    
    Схема подключения:
    ARK127 -> С2000М
    SC39-40 -> Табло "Выход"
    SC41-42 -> Маяк-12-3М (сирена)
    
    Устройства размещены:
    - ДИП-34А в коридоре первого этажа
    - ИПР 513 у эвакуационных выходов
    - Табло над выходами из здания
    """
    
    # Анализ
    result = analyze_project_description(test_text)
    
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ NLP-АНАЛИЗА")
    print("=" * 60)
    print(f"\nКраткое содержание: {result.summary}\n")
    
    print("Извлеченные устройства:")
    for entity in result.device_mentions[:10]:
        print(f"  • {entity.text} → {entity.normalized_form} (уверенность: {entity.confidence:.2f})")
        if entity.context:
            print(f"    Контекст: ...{entity.context}...")
    
    print(f"\nВсего сущностей: {len(result.entities)}")
    print(f"Связей выявлено: {len(result.relations)}")
    
    if result.relations:
        print("\nВыявленные связи:")
        for rel in result.relations[:5]:
            print(f"  • {rel['source']} → {rel['target']} ({rel['type']}, уверенность: {rel['confidence']:.2f})")
