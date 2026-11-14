import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { Text } from '@/components/Themed';
import { useProjects } from '@/hooks/use-projects';
import {
  type Project,
  type ProjectStatus,
} from '@/lib/projects/project-service';
import { getApiErrorMessage } from '@/lib/api/api-errors';

const STATUS_STYLES: Record<
  ProjectStatus,
  { label: string; color: string; background: string }
> = {
  planned: {
    label: 'Planned',
    color: '#64748B',
    background: '#64748B18',
  },
  active: {
    label: 'Active',
    color: '#059669',
    background: '#05966918',
  },
  paused: {
    label: 'Paused',
    color: '#D97706',
    background: '#D9770618',
  },
  completed: {
    label: 'Completed',
    color: '#2563EB',
    background: '#2563EB18',
  },
  archived: {
    label: 'Archived',
    color: '#64748B',
    background: '#64748B18',
  },
};

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Date unavailable';
  }

  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function ProjectItem({
  project,
  theme,
}: {
  project: Project;
  theme: (typeof Colors)['light'];
}) {
  const status = STATUS_STYLES[project.status];

  return (
    <View
      style={[
        styles.projectCard,
        {
          backgroundColor: theme.surface,
          borderColor: theme.border,
        },
      ]}
    >
      <View style={styles.projectTopRow}>
        <View style={styles.projectInfo}>
          <Text style={styles.projectName}>{project.name}</Text>
          <Text style={[styles.projectSlug, { color: theme.muted }]}>
            {project.slug}
          </Text>
        </View>

        <View
          style={[
            styles.statusBadge,
            { backgroundColor: status.background },
          ]}
        >
          <Text style={[styles.statusText, { color: status.color }]}>
            {status.label}
          </Text>
        </View>
      </View>

      {project.description ? (
        <Text style={[styles.projectDescription, { color: theme.muted }]}>
          {project.description}
        </Text>
      ) : (
        <Text style={[styles.projectDescription, { color: theme.muted }]}>
          No description provided.
        </Text>
      )}

      <View style={[styles.projectDivider, { backgroundColor: theme.border }]} />

      <View style={styles.projectFooter}>
        <Text style={[styles.dateLabel, { color: theme.muted }]}>
          Last updated
        </Text>
        <Text style={[styles.dateValue, { color: theme.muted }]}>
          {formatDate(project.updated_at)}
        </Text>
      </View>
    </View>
  );
}

export default function ProjectsScreen() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];
  const insets = useSafeAreaInsets();

  const {
    projects,
    isLoading,
    isCreating,
    error,
    refresh,
    create,
  } = useProjects();

  const [search, setSearch] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return projects;
    }

    return projects.filter((project) => (
      project.name.toLowerCase().includes(query)
      || project.slug.toLowerCase().includes(query)
      || (project.description ?? '').toLowerCase().includes(query)
    ));
  }, [projects, search]);

  async function handleCreateProject() {
    const name = projectName.trim();
    const cleanedDescription = description.trim();

    setFormError(null);
    setSuccessMessage(null);

    if (name.length < 2 || name.length > 150) {
      setFormError('Project name must contain between 2 and 150 characters.');
      return;
    }

    if (cleanedDescription.length > 2000) {
      setFormError('Description cannot exceed 2,000 characters.');
      return;
    }

    try {
      const project = await create({
        name,
        description: cleanedDescription || null,
      });

      setProjectName('');
      setDescription('');
      setShowCreateForm(false);
      setSearch('');
      setSuccessMessage(`"${project.name}" was created successfully.`);
    } catch (err) {
      setFormError(
        getApiErrorMessage(err, 'Unable to create the project. Please try again.'),
      );
    }
  }

  return (
    <KeyboardAvoidingView
      style={[styles.screen, { backgroundColor: theme.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.container,
          {
            paddingTop: insets.top + 20,
            paddingBottom: Math.max(insets.bottom, 24) + 24,
          },
        ]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={() => void refresh()}
            tintColor={theme.tint}
            colors={[theme.tint]}
          />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={[styles.eyebrow, { color: theme.muted }]}>
              WORKSPACE
            </Text>
            <Text style={styles.heading}>Projects</Text>
            <Text style={[styles.subtitle, { color: theme.muted }]}>
              Manage and track your workspace projects.
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Create a project"
            onPress={() => {
              setShowCreateForm((current) => !current);
              setFormError(null);
              setSuccessMessage(null);
            }}
            style={({ pressed }) => [
              styles.addButton,
              {
                backgroundColor: theme.tint,
                opacity: pressed ? 0.75 : 1,
              },
            ]}
          >
            <Text style={styles.addButtonText}>
              {showCreateForm ? 'Cancel' : '+ New'}
            </Text>
          </Pressable>
        </View>

        <View style={styles.summaryRow}>
          <View
            style={[
              styles.summaryCard,
              { backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          >
            <Text style={[styles.summaryLabel, { color: theme.muted }]}>
              Total projects
            </Text>
            <Text style={styles.summaryValue}>{projects.length}</Text>
          </View>

          <View
            style={[
              styles.summaryCard,
              { backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          >
            <Text style={[styles.summaryLabel, { color: theme.muted }]}>
              Active projects
            </Text>
            <Text style={styles.summaryValue}>
              {projects.filter((project) => project.status === 'active').length}
            </Text>
          </View>
        </View>

        {successMessage ? (
          <View style={styles.successBanner}>
            <Text style={styles.successText}>{successMessage}</Text>
          </View>
        ) : null}

        {showCreateForm ? (
          <View
            style={[
              styles.formCard,
              { backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          >
            <Text style={styles.formTitle}>Create a project</Text>
            <Text style={[styles.formSubtitle, { color: theme.muted }]}>
              Add a project to your workspace.
            </Text>

            <Text style={styles.inputLabel}>Project name</Text>
            <TextInput
              value={projectName}
              onChangeText={setProjectName}
              placeholder="e.g. Website redesign"
              placeholderTextColor={theme.muted}
              maxLength={150}
              autoCapitalize="sentences"
              returnKeyType="next"
              editable={!isCreating}
              style={[
                styles.input,
                {
                  color: theme.text,
                  backgroundColor: theme.background,
                  borderColor: theme.border,
                },
              ]}
            />

            <View style={styles.descriptionLabelRow}>
              <Text style={styles.inputLabel}>Description</Text>
              <Text style={[styles.characterCount, { color: theme.muted }]}>
                {description.length}/2000
              </Text>
            </View>

            <TextInput
              value={description}
              onChangeText={setDescription}
              placeholder="What is this project about? (Optional)"
              placeholderTextColor={theme.muted}
              maxLength={2000}
              multiline
              textAlignVertical="top"
              editable={!isCreating}
              style={[
                styles.input,
                styles.descriptionInput,
                {
                  color: theme.text,
                  backgroundColor: theme.background,
                  borderColor: theme.border,
                },
              ]}
            />

            {formError ? (
              <Text style={styles.errorText}>{formError}</Text>
            ) : null}

            <Pressable
              accessibilityRole="button"
              disabled={isCreating}
              onPress={() => void handleCreateProject()}
              style={({ pressed }) => [
                styles.submitButton,
                {
                  backgroundColor: theme.tint,
                  opacity: isCreating ? 0.6 : pressed ? 0.75 : 1,
                },
              ]}
            >
              {isCreating ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.submitButtonText}>Create project</Text>
              )}
            </Pressable>
          </View>
        ) : null}

        <View style={styles.listHeader}>
          <View>
            <Text style={styles.sectionTitle}>All projects</Text>
            <Text style={[styles.sectionSubtitle, { color: theme.muted }]}>
              {projects.length} project{projects.length === 1 ? '' : 's'} in your workspace
            </Text>
          </View>
        </View>

        <TextInput
          value={search}
          onChangeText={setSearch}
          placeholder="Search projects..."
          placeholderTextColor={theme.muted}
          autoCapitalize="none"
          returnKeyType="search"
          style={[
            styles.searchInput,
            {
              color: theme.text,
              backgroundColor: theme.surface,
              borderColor: theme.border,
            },
          ]}
        />

        {isLoading && projects.length === 0 ? (
          <View style={styles.stateContainer}>
            <ActivityIndicator size="large" color={theme.tint} />
            <Text style={[styles.stateText, { color: theme.muted }]}>
              Loading your projects...
            </Text>
          </View>
        ) : error && projects.length === 0 ? (
          <View
            style={[
              styles.stateCard,
              { backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          >
            <Text style={styles.stateTitle}>Unable to load projects</Text>
            <Text style={[styles.stateText, { color: theme.muted }]}>
              {error}
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => void refresh()}
              style={[styles.retryButton, { backgroundColor: theme.tint }]}
            >
              <Text style={styles.retryButtonText}>Try again</Text>
            </Pressable>
          </View>
        ) : filteredProjects.length === 0 ? (
          <View
            style={[
              styles.stateCard,
              { backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          >
            <Text style={styles.stateTitle}>
              {search.trim() ? 'No matching projects' : 'No projects yet'}
            </Text>
            <Text style={[styles.stateText, { color: theme.muted }]}>
              {search.trim()
                ? 'Try another search term.'
                : 'Create your first project to get started.'}
            </Text>
            {!search.trim() ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => setShowCreateForm(true)}
                style={[styles.retryButton, { backgroundColor: theme.tint }]}
              >
                <Text style={styles.retryButtonText}>Create your first project</Text>
              </Pressable>
            ) : null}
          </View>
        ) : (
          <View style={styles.projectsList}>
            {filteredProjects.map((project) => (
              <ProjectItem
                key={project.id}
                project={project}
                theme={theme}
              />
            ))}
          </View>
        )}

        {error && projects.length > 0 ? (
          <Text style={styles.warningText}>
            Refresh failed: {error}. Showing the last loaded projects.
          </Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: 20,
    gap: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  headerText: {
    flex: 1,
    gap: 5,
  },
  eyebrow: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  heading: {
    fontSize: 28,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 13,
    lineHeight: 19,
  },
  addButton: {
    minHeight: 42,
    paddingHorizontal: 15,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
  summaryRow: {
    flexDirection: 'row',
    gap: 12,
  },
  summaryCard: {
    flex: 1,
    padding: 16,
    borderWidth: 1,
    borderRadius: 16,
    gap: 8,
  },
  summaryLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
  summaryValue: {
    fontSize: 26,
    fontWeight: '800',
  },
  successBanner: {
    padding: 13,
    borderRadius: 12,
    backgroundColor: '#05966918',
  },
  successText: {
    color: '#059669',
    fontSize: 13,
    fontWeight: '600',
  },
  formCard: {
    padding: 17,
    borderWidth: 1,
    borderRadius: 16,
    gap: 12,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: '800',
  },
  formSubtitle: {
    fontSize: 12,
    marginTop: -7,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '700',
  },
  descriptionLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  characterCount: {
    fontSize: 11,
  },
  input: {
    minHeight: 46,
    paddingHorizontal: 12,
    paddingVertical: 11,
    borderWidth: 1,
    borderRadius: 10,
    fontSize: 14,
  },
  descriptionInput: {
    minHeight: 105,
  },
  errorText: {
    color: '#DC2626',
    fontSize: 12,
    lineHeight: 18,
  },
  submitButton: {
    minHeight: 46,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 3,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  listHeader: {
    marginBottom: -12,
  },
  sectionTitle: {
    fontSize: 19,
    fontWeight: '800',
  },
  sectionSubtitle: {
    fontSize: 12,
    marginTop: 4,
  },
  searchInput: {
    minHeight: 46,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderRadius: 12,
    fontSize: 14,
  },
  projectsList: {
    gap: 12,
  },
  projectCard: {
    padding: 16,
    borderWidth: 1,
    borderRadius: 16,
    gap: 12,
  },
  projectTopRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  projectInfo: {
    flex: 1,
    gap: 4,
  },
  projectName: {
    fontSize: 16,
    fontWeight: '800',
  },
  projectSlug: {
    fontSize: 11,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '800',
  },
  projectDescription: {
    fontSize: 13,
    lineHeight: 19,
  },
  projectDivider: {
    height: 1,
  },
  projectFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  dateLabel: {
    fontSize: 11,
  },
  dateValue: {
    fontSize: 11,
    fontWeight: '600',
  },
  stateContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 42,
    gap: 12,
  },
  stateCard: {
    alignItems: 'center',
    padding: 22,
    borderWidth: 1,
    borderRadius: 16,
    gap: 12,
  },
  stateTitle: {
    fontSize: 16,
    fontWeight: '800',
    textAlign: 'center',
  },
  stateText: {
    fontSize: 13,
    lineHeight: 19,
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 17,
    paddingVertical: 11,
    borderRadius: 10,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  warningText: {
    color: '#D97706',
    fontSize: 12,
    lineHeight: 18,
  },
});
