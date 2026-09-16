import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { colors } from '../theme/colors';
import { fetchApi } from '../api/client';

export default function MarketPulseScreen() {
  const [pulse, setPulse] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPulse();
  }, []);

  const loadPulse = async () => {
    try {
      const data = await fetchApi('/market/pulse');
      setPulse(data);
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <View style={[styles.container, { justifyContent: 'center' }]}><ActivityIndicator size="large" color={colors.accentBlue} /></View>;
  }

  const regimeColor = pulse?.regime === 'BULL' ? colors.accentGreen : pulse?.regime === 'BEAR' ? colors.accentRed : colors.accentYellow;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Market Pulse</Text>
      <Text style={styles.subHeader}>Real-time Indian equity market regime and breadth</Text>
      
      <View style={styles.card}>
        <Text style={styles.cardLabel}>CURRENT MARKET REGIME</Text>
        <View style={styles.row}>
          <View style={[styles.badge, { backgroundColor: regimeColor + '33', borderColor: regimeColor }]}>
            <Text style={[styles.badgeText, { color: regimeColor }]}>{pulse?.regime || 'UNKNOWN'}</Text>
          </View>
          <Text style={styles.confidenceText}>{((pulse?.regime_confidence || 0) * 100).toFixed(0)}% confidence</Text>
        </View>
      </View>
      
      <View style={styles.grid}>
        <View style={styles.gridCard}>
          <Text style={styles.cardLabel}>NIFTY 50</Text>
          <Text style={styles.largeValue}>{pulse?.nifty_close?.toFixed(0) || '—'}</Text>
          <Text style={[styles.changeText, { color: (pulse?.nifty_change_pct || 0) >= 0 ? colors.accentGreen : colors.accentRed }]}>
            {(pulse?.nifty_change_pct || 0) >= 0 ? '+' : ''}{pulse?.nifty_change_pct?.toFixed(2) || '0'}%
          </Text>
        </View>
        <View style={styles.gridCard}>
          <Text style={styles.cardLabel}>Market Breadth</Text>
          <Text style={styles.largeValue}>{pulse?.advances || 0}:{pulse?.declines || 0}</Text>
          <Text style={styles.changeText}>Adv/Dec</Text>
        </View>
      </View>
      
      <View style={styles.disclaimer}>
        <Text style={styles.disclaimerText}>
          Disclaimer: This is a decision-support tool. It is not financial advice.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
    padding: 20,
  },
  header: {
    fontSize: 28,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginBottom: 4,
  },
  subHeader: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 24,
  },
  card: {
    backgroundColor: colors.bgCard,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
  },
  cardLabel: {
    fontSize: 11,
    color: colors.textMuted,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    marginRight: 12,
  },
  badgeText: {
    fontWeight: 'bold',
    fontSize: 12,
  },
  confidenceText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  grid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  gridCard: {
    backgroundColor: colors.bgCard,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    width: '48%',
  },
  largeValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  changeText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
  },
  disclaimer: {
    backgroundColor: colors.bgSecondary,
    padding: 16,
    borderRadius: 8,
    marginTop: 20,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  disclaimerText: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  }
});
