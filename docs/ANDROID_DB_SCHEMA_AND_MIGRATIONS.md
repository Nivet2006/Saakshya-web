# Android Database Schema, Date Formats & Room Migrations

This document specifies the local Android SQLite/Room database schema, date conversion policies, and migration scripts for the **ASHA Voice Field Register** Android client (Agent 2).

The schema is grounded in the published canonical contracts:
- [`shared-contracts/visit.schema.json`](../shared-contracts/visit.schema.json)
- [`shared-contracts/danger-alert.schema.json`](../shared-contracts/danger-alert.schema.json)
- [`shared-contracts/voice-events.schema.json`](../shared-contracts/voice-events.schema.json)
- [`docs/INTEGRATION_HANDOFF.md`](./INTEGRATION_HANDOFF.md)

---

## 1. Schema Location in Workspace

The technology-independent canonical contract definitions are stored in:
- `shared-contracts/visit.schema.json`
- `shared-contracts/danger-alert.schema.json`
- `shared-contracts/voice-events.schema.json`
- `shared-contracts/openapi.json`

The Android app implementation target is:
`..\sakshya android\` (or `android/` within project root).

---

## 2. Date & Timezone Standards

All dates and timestamps in the database follow strict public-health standards:

| Field Type | Storage Representation | Timezone / Format | Example | Kotlin Type |
|---|---|---|---|---|
| **Event Timestamps** (`created_at`, `confirmed_at`, `committed_at`, `detected_at`) | `TEXT` | UTC ISO-8601 (`date-time`) | `2026-11-22T01:45:00.000Z` | `java.time.Instant` / `String` |
| **Calendar Clinical Dates** (`next_visit_date`, `due_date`, `edd_date`, `lmp_date`) | `TEXT` | ISO-8601 Date (`YYYY-MM-DD`) in **`Asia/Kolkata`** | `2026-12-05` | `java.time.LocalDate` / `String` |

---

## 3. Room Database Entity Definitions (Kotlin)

### 3.1 Beneficiary Entity (`beneficiaries`)

```kotlin
package com.sakshya.asha.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "beneficiaries",
    indices = [
        Index(value = ["beneficiary_id"], unique = true),
        Index(value = ["assigned_asha_id"]),
        Index(value = ["high_risk_status"])
    ]
)
data class BeneficiaryEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String, // UUID or c0000000-...

    @ColumnInfo(name = "beneficiary_id")
    val beneficiaryId: String, // e.g. "BEN-1042"

    @ColumnInfo(name = "full_name")
    val fullName: String,

    @ColumnInfo(name = "age_years")
    val ageYears: Int,

    @ColumnInfo(name = "gender")
    val gender: String, // FEMALE, MALE, OTHER

    @ColumnInfo(name = "category")
    val category: String, // PREGNANT_WOMAN, LACTATING_MOTHER, INFANT, CHILD

    @ColumnInfo(name = "village")
    val village: String,

    @ColumnInfo(name = "household_head")
    val householdHead: String?,

    @ColumnInfo(name = "phone_number")
    val phoneNumber: String?,

    @ColumnInfo(name = "rch_id")
    val rchId: String?,

    @ColumnInfo(name = "lmp_date")
    val lmpDate: String?, // YYYY-MM-DD (Asia/Kolkata)

    @ColumnInfo(name = "edd_date")
    val eddDate: String?, // YYYY-MM-DD (Asia/Kolkata)

    @ColumnInfo(name = "high_risk_status")
    val highRiskStatus: Boolean,

    @ColumnInfo(name = "high_risk_reasons")
    val highRiskReasons: List<String>,

    @ColumnInfo(name = "assigned_asha_id")
    val assignedAshaId: String,

    @ColumnInfo(name = "phc_id")
    val phcId: String,

    @ColumnInfo(name = "preferred_language")
    val preferredLanguage: String, // e.g. "hi-IN"

    @ColumnInfo(name = "created_at")
    val createdAt: String, // UTC ISO-8601

    @ColumnInfo(name = "updated_at")
    val updatedAt: String // UTC ISO-8601
)
```

---

### 3.2 Visit Record Entity (`visits`)

```kotlin
package com.sakshya.asha.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "visits",
    indices = [
        Index(value = ["visit_id"], unique = true),
        Index(value = ["session_id"]),
        Index(value = ["beneficiary_id"]),
        Index(value = ["sync_status"]),
        Index(value = ["danger_sign_flagged"])
    ]
)
data class VisitEntity(
    @PrimaryKey
    @ColumnInfo(name = "visit_id")
    val visitId: String,

    @ColumnInfo(name = "session_id")
    val sessionId: String,

    @ColumnInfo(name = "worker_id")
    val workerId: String,

    @ColumnInfo(name = "beneficiary_id")
    val beneficiaryId: String?, // BEN-xxxx or null

    @ColumnInfo(name = "beneficiary_name")
    val beneficiaryName: String?,

    @ColumnInfo(name = "visit_type")
    val visitType: String?, // ANC, PNC, Newborn, Immunisation, null

    @ColumnInfo(name = "weight_kg")
    val weightKg: Double?,

    @ColumnInfo(name = "weight_source_text")
    val weightSourceText: String?,

    @ColumnInfo(name = "vaccinations_completed")
    val vaccinationsCompleted: List<String>,

    @ColumnInfo(name = "vaccinations_due")
    val vaccinationsDue: List<String>,

    @ColumnInfo(name = "next_visit_date")
    val nextVisitDate: String?, // YYYY-MM-DD (Asia/Kolkata)

    @ColumnInfo(name = "next_visit_date_source_text")
    val nextVisitDateSourceText: String?,

    @ColumnInfo(name = "danger_signs")
    val dangerSigns: List<String>,

    @ColumnInfo(name = "danger_sign_flagged")
    val dangerSignFlagged: Boolean,

    @ColumnInfo(name = "follow_up_actions_json")
    val followUpActionsJson: String, // JSON serialized array of FollowUpActionV1

    @ColumnInfo(name = "status")
    val status: String, // draft, confirmed, committed

    @ColumnInfo(name = "confirmed_at")
    val confirmedAt: String?, // UTC ISO-8601

    @ColumnInfo(name = "committed_at")
    val committedAt: String?, // UTC ISO-8601

    @ColumnInfo(name = "persistence_record_id")
    val persistenceRecordId: String?,

    @ColumnInfo(name = "language")
    val language: String,

    @ColumnInfo(name = "timezone")
    val timezone: String = "Asia/Kolkata",

    @ColumnInfo(name = "synthetic")
    val synthetic: Boolean = true,

    // Sync Management Columns for Offline-First Architecture
    @ColumnInfo(name = "sync_status", defaultValue = "'PENDING'")
    val syncStatus: String, // PENDING, SYNCING, SYNCED, ERROR

    @ColumnInfo(name = "firebase_doc_id")
    val firebaseDocId: String?,

    @ColumnInfo(name = "last_synced_at")
    val lastSyncedAt: String? // UTC ISO-8601
)
```

---

### 3.3 Danger Alert Entity (`danger_alerts`)

```kotlin
package com.sakshya.asha.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "danger_alerts",
    indices = [
        Index(value = ["alert_id"], unique = true),
        Index(value = ["beneficiary_id"]),
        Index(value = ["status"])
    ]
)
data class DangerAlertEntity(
    @PrimaryKey
    @ColumnInfo(name = "alert_id")
    val alertId: String,

    @ColumnInfo(name = "session_id")
    val sessionId: String?,

    @ColumnInfo(name = "visit_id")
    val visitId: String?,

    @ColumnInfo(name = "beneficiary_id")
    val beneficiaryId: String?,

    @ColumnInfo(name = "beneficiary_name")
    val beneficiaryName: String?,

    @ColumnInfo(name = "canonical_danger_sign_id")
    val canonicalDangerSignId: String,

    @ColumnInfo(name = "canonical_name")
    val canonicalName: String,

    @ColumnInfo(name = "subject")
    val subject: String, // mother, newborn, infant

    @ColumnInfo(name = "category")
    val category: String, // ANC, Intranatal, PNC, Newborn

    @ColumnInfo(name = "supporting_evidence")
    val supportingEvidence: String,

    @ColumnInfo(name = "source_guideline_ref")
    val sourceGuidelineRef: String, // NHM citation

    @ColumnInfo(name = "referral_message")
    val referralMessage: String,

    @ColumnInfo(name = "status")
    val status: String, // active, acknowledged, referred, resolved

    @ColumnInfo(name = "detected_at")
    val detectedAt: String, // UTC ISO-8601

    @ColumnInfo(name = "acknowledged_at")
    val acknowledgedAt: String?,

    @ColumnInfo(name = "acknowledged_by")
    val acknowledgedBy: String?,

    @ColumnInfo(name = "sync_status", defaultValue = "'PENDING'")
    val syncStatus: String
)
```

---

### 3.4 Follow-Up Task Entity (`follow_up_tasks`)

```kotlin
package com.sakshya.asha.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "follow_up_tasks",
    indices = [
        Index(value = ["due_date"]),
        Index(value = ["status"]),
        Index(value = ["beneficiary_id"])
    ]
)
data class FollowUpTaskEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "beneficiary_id")
    val beneficiaryId: String,

    @ColumnInfo(name = "beneficiary_name")
    val beneficiaryName: String?,

    @ColumnInfo(name = "asha_worker_id")
    val ashaWorkerId: String,

    @ColumnInfo(name = "phc_id")
    val phcId: String,

    @ColumnInfo(name = "due_date")
    val dueDate: String, // YYYY-MM-DD (Asia/Kolkata)

    @ColumnInfo(name = "task_type")
    val taskType: String,

    @ColumnInfo(name = "action_type")
    val actionType: String,

    @ColumnInfo(name = "priority")
    val priority: String, // URGENT, HIGH, NORMAL

    @ColumnInfo(name = "status")
    val status: String, // PENDING, OVERDUE, COMPLETED, CANCELLED

    @ColumnInfo(name = "notes")
    val notes: String?,

    @ColumnInfo(name = "created_at")
    val createdAt: String, // UTC ISO-8601

    @ColumnInfo(name = "completed_at")
    val completedAt: String?
)
```

---

## 4. Room Type Converters

```kotlin
package com.sakshya.asha.data.local.converters

import androidx.room.TypeConverter
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class RoomConverters {
    private val json = Json { ignoreUnknownKeys = true }

    @TypeConverter
    fun fromStringList(value: List<String>?): String {
        return value?.let { json.encodeToString(it) } ?: "[]"
    }

    @TypeConverter
    fun toStringList(value: String?): List<String> {
        return value?.let {
            try { json.decodeFromString(it) } catch (e: Exception) { emptyList() }
        } ?: emptyList()
    }
}
```

---

## 5. Room Database Migrations

### Migration 1 to 2: Add Firebase Cloud Sync Tracking

```kotlin
package com.sakshya.asha.data.local.migrations

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Migration 1 -> 2:
 * Adds offline sync management fields (sync_status, firebase_doc_id, last_synced_at)
 * to support Firebase Firestore / Cloud synchronization.
 */
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(database: SupportSQLiteDatabase) {
        // 1. Alter visits table for cloud sync
        database.execSQL(
            "ALTER TABLE visits ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'PENDING'"
        )
        database.execSQL(
            "ALTER TABLE visits ADD COLUMN firebase_doc_id TEXT DEFAULT NULL"
        )
        database.execSQL(
            "ALTER TABLE visits ADD COLUMN last_synced_at TEXT DEFAULT NULL"
        )
        database.execSQL(
            "CREATE INDEX IF NOT EXISTS index_visits_sync_status ON visits(sync_status)"
        )

        // 2. Alter danger_alerts table for cloud sync
        database.execSQL(
            "ALTER TABLE danger_alerts ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'PENDING'"
        )
        database.execSQL(
            "CREATE INDEX IF NOT EXISTS index_danger_alerts_sync_status ON danger_alerts(sync_status)"
        )

        // 3. Create follow_up_tasks table if not exists
        database.execSQL("""
            CREATE TABLE IF NOT EXISTS follow_up_tasks (
                id TEXT NOT NULL PRIMARY KEY,
                beneficiary_id TEXT NOT NULL,
                beneficiary_name TEXT,
                asha_worker_id TEXT NOT NULL,
                phc_id TEXT NOT NULL,
                due_date TEXT NOT NULL,
                task_type TEXT NOT NULL,
                action_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """.trimIndent())
        database.execSQL("CREATE INDEX IF NOT EXISTS index_fu_due_date ON follow_up_tasks(due_date)")
        database.execSQL("CREATE INDEX IF NOT EXISTS index_fu_status ON follow_up_tasks(status)")
    }
}
```

---

## 6. App Database Class

```kotlin
package com.sakshya.asha.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.sakshya.asha.data.local.converters.RoomConverters
import com.sakshya.asha.data.local.dao.BeneficiaryDao
import com.sakshya.asha.data.local.dao.DangerAlertDao
import com.sakshya.asha.data.local.dao.FollowUpTaskDao
import com.sakshya.asha.data.local.dao.VisitDao
import com.sakshya.asha.data.local.entity.BeneficiaryEntity
import com.sakshya.asha.data.local.entity.DangerAlertEntity
import com.sakshya.asha.data.local.entity.FollowUpTaskEntity
import com.sakshya.asha.data.local.entity.VisitEntity

@Database(
    entities = [
        BeneficiaryEntity::class,
        VisitEntity::class,
        DangerAlertEntity::class,
        FollowUpTaskEntity::class
    ],
    version = 2,
    exportSchema = true
)
@TypeConverters(RoomConverters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun beneficiaryDao(): BeneficiaryDao
    abstract fun visitDao(): VisitDao
    abstract fun dangerAlertDao(): DangerAlertDao
    abstract fun followUpTaskDao(): FollowUpTaskDao
}
```

---

## 7. Firebase Sync Integration for Android

In Android (`build.gradle.kts`):
```kotlin
dependencies {
    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    // Firebase Android SDK
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-firestore-ktx")
    implementation("com.google.firebase:firebase-auth-ktx")
}
```

When network is available, the Android `WorkManager` reads pending records (`WHERE sync_status = 'PENDING'`) and pushes them to Firebase Firestore collections (`visits`, `danger_alerts`, `beneficiaries`), updating `sync_status = 'SYNCED'`.
